from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PortalError
from app.d365.client import D365Client
from app.d365.query import ODataQuery, and_all, equals, validate_identifier
from app.database.models import D365EntityMapping, EmployeeIdentityMapping
from app.employees.schemas import LeaveBalance, LeaveBalancesResponse

LEAVE_BALANCE_FIELDS = {"leaveType", "taken", "total", "available", "hidden"}


class D365LeaveService:
    def __init__(self, session: AsyncSession, client: D365Client) -> None:
        self._session = session
        self._client = client

    async def get_balances(self, identity: EmployeeIdentityMapping) -> LeaveBalancesResponse:
        configuration = await self._configuration("leave_balance", required=True)
        assert configuration is not None
        records, fields = await self._records(configuration, identity)

        if not records:
            fallback = await self._configuration("leave_balance_active", required=False)
            if fallback is not None:
                records, fields = await self._records(fallback, identity)

        balances: list[LeaveBalance] = []
        for raw in records:
            if "hidden" in fields and self._is_hidden(raw.get(fields["hidden"])):
                continue
            leave_type = self._required_value(raw.get(fields["leaveType"]))
            balances.append(
                LeaveBalance(
                    leaveType=leave_type,
                    available=self._number(raw.get(fields.get("available", ""))),
                    taken=self._number(raw.get(fields.get("taken", ""))),
                    total=self._number(raw.get(fields.get("total", ""))),
                )
            )
        return LeaveBalancesResponse(balances=balances)

    async def _records(
        self,
        configuration: D365EntityMapping,
        identity: EmployeeIdentityMapping,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        fields = self._validated_fields(configuration.field_mapping)
        personnel_field = self._required_identifier(configuration.personnel_number_field)
        selected = [personnel_field, *fields.values()]
        filters = [equals(personnel_field, identity.d365_personnel_number)]
        if configuration.company_field and identity.d365_company:
            selected.append(configuration.company_field)
            filters.append(equals(configuration.company_field, identity.d365_company))

        payload = await self._client.get_entity(
            configuration.entity_name,
            ODataQuery(
                select=tuple(dict.fromkeys(selected)),
                filter_expression=and_all(*filters),
                top=100,
                cross_company=bool(configuration.company_field and identity.d365_company),
            ),
        )
        records = payload.get("value")
        if not isinstance(records, list):
            raise PortalError("LEAVE_UNAVAILABLE", "Your leave balances are unavailable.", 503)

        validated: list[dict[str, Any]] = []
        for raw in records:
            if not isinstance(raw, dict):
                raise PortalError("LEAVE_CONFLICT", "Leave balance data requires review.", 409)
            if str(raw.get(personnel_field, "")) != identity.d365_personnel_number:
                raise PortalError(
                    "LEAVE_CONFLICT", "Leave balance identity validation failed.", 409
                )
            if configuration.company_field and identity.d365_company:
                returned_company = str(raw.get(configuration.company_field, ""))
                if returned_company.casefold() != identity.d365_company.casefold():
                    raise PortalError(
                        "LEAVE_CONFLICT", "Leave balance company validation failed.", 409
                    )
            validated.append(raw)
        return validated, fields

    async def _configuration(
        self, mapping_key: str, *, required: bool
    ) -> D365EntityMapping | None:
        configuration = await self._session.scalar(
            select(D365EntityMapping).where(
                D365EntityMapping.mapping_key == mapping_key,
                D365EntityMapping.enabled.is_(True),
            )
        )
        # The key check also makes simplistic test doubles fail closed rather than
        # accidentally reusing the primary entity as its own fallback.
        if configuration is not None and configuration.mapping_key != mapping_key:
            configuration = None
        if configuration is None and required:
            raise PortalError(
                "LEAVE_NOT_CONFIGURED", "Leave balance integration has not been enabled.", 503
            )
        if configuration is None:
            return None
        validate_identifier(configuration.entity_name)
        if configuration.company_field:
            validate_identifier(configuration.company_field)
        return configuration

    @staticmethod
    def _is_hidden(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"true", "yes", "1"}:
                return True
            if normalized in {"false", "no", "0"}:
                return False
        raise PortalError("LEAVE_CONFLICT", "Leave balance visibility is invalid.", 409)

    @staticmethod
    def _validated_fields(raw: dict[str, Any]) -> dict[str, str]:
        fields = {
            key: validate_identifier(value)
            for key, value in raw.items()
            if key in LEAVE_BALANCE_FIELDS and isinstance(value, str)
        }
        if "leaveType" not in fields:
            raise PortalError("LEAVE_NOT_CONFIGURED", "Leave mapping is incomplete.", 503)
        return fields

    @staticmethod
    def _required_identifier(value: str | None) -> str:
        if not value:
            raise PortalError("LEAVE_NOT_CONFIGURED", "Leave identity field is missing.", 503)
        return validate_identifier(value)

    @staticmethod
    def _required_value(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PortalError("LEAVE_CONFLICT", "Leave type is missing.", 409)
        return value

    @staticmethod
    def _number(value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise PortalError("LEAVE_CONFLICT", "Leave balance value is invalid.", 409)
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise PortalError("LEAVE_CONFLICT", "Leave balance value is invalid.", 409) from exc
