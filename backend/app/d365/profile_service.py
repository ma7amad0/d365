from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PortalError
from app.d365.client import D365Client
from app.d365.query import ODataQuery, and_all, equals, validate_identifier
from app.database.models import D365EntityMapping, EmployeeIdentityMapping
from app.employees.schemas import EmployeeProfile, EmployeeProfileResponse

PROFILE_FIELDS = {
    "personnelNumber",
    "displayName",
    "email",
    "phone",
    "officeLocation",
    "professionalTitle",
    "legalEntity",
    "employmentStartDate",
    "employmentEndDate",
}


class D365ProfileService:
    def __init__(self, session: AsyncSession, client: D365Client) -> None:
        self._session = session
        self._client = client

    async def get_profile(self, identity: EmployeeIdentityMapping) -> EmployeeProfileResponse:
        configuration = await self._configuration()
        fields = self._validated_fields(configuration.field_mapping)
        filters = [
            equals(
                self._required_identifier(configuration.personnel_number_field),
                identity.d365_personnel_number,
            )
        ]
        if configuration.company_field and identity.d365_company:
            filters.append(equals(configuration.company_field, identity.d365_company))
        payload = await self._client.get_entity(
            configuration.entity_name,
            ODataQuery(
                select=tuple(dict.fromkeys(fields.values())),
                filter_expression=and_all(*filters),
                top=2,
            ),
        )
        records = payload.get("value")
        if not isinstance(records, list):
            raise PortalError(
                "PROFILE_UNAVAILABLE", "Your employee information is unavailable.", 503
            )
        if len(records) > 1:
            raise PortalError(
                "PROFILE_CONFLICT",
                "Multiple employee records require administrator review.",
                409,
            )
        if not records or not isinstance(records[0], dict):
            raise PortalError("PROFILE_NOT_FOUND", "Your employee profile was not found.", 404)
        record: dict[str, Any] = records[0]
        values = {
            logical: self._optional_scalar(record.get(field)) for logical, field in fields.items()
        }
        personnel_number = values.get("personnelNumber")
        if (
            not isinstance(personnel_number, str)
            or personnel_number != identity.d365_personnel_number
        ):
            raise PortalError(
                "PROFILE_CONFLICT", "Employee record identity validation failed.", 409
            )
        return EmployeeProfileResponse(employee=EmployeeProfile(**values))

    async def _configuration(self) -> D365EntityMapping:
        statement = select(D365EntityMapping).where(
            D365EntityMapping.mapping_key == "profile",
            D365EntityMapping.enabled.is_(True),
        )
        configuration = await self._session.scalar(statement)
        if configuration is None:
            raise PortalError(
                "PROFILE_NOT_CONFIGURED",
                "Employee profile integration has not been enabled.",
                503,
            )
        validate_identifier(configuration.entity_name)
        return configuration

    @staticmethod
    def _validated_fields(raw: dict[str, Any]) -> dict[str, str]:
        fields = {
            key: validate_identifier(value)
            for key, value in raw.items()
            if key in PROFILE_FIELDS and isinstance(value, str)
        }
        if "personnelNumber" not in fields:
            raise PortalError("PROFILE_NOT_CONFIGURED", "Profile field mapping is incomplete.", 503)
        return fields

    @staticmethod
    def _required_identifier(value: str | None) -> str:
        if not value:
            raise PortalError("PROFILE_NOT_CONFIGURED", "Profile identity field is missing.", 503)
        return validate_identifier(value)

    @staticmethod
    def _optional_scalar(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str | int | float | bool):
            return str(value)
        return None
