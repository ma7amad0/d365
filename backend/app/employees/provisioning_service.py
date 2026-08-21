from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import AuthenticatedUser
from app.core.exceptions import PortalError
from app.d365.client import D365Client
from app.d365.exceptions import D365Error
from app.d365.query import ODataQuery, equals, validate_identifier
from app.database.models import (
    D365EntityMapping,
    EmployeeIdentityMapping,
    EmployeeIdentityMappingHistory,
)

REQUIRED_IDENTITY_FIELDS = {"entraOid", "entraUpn", "personnelNumber", "company"}


class IdentityProvisioningService:
    """Create a local mapping only after D365 confirms the signed Entra object ID."""

    def __init__(self, session: AsyncSession, client: D365Client) -> None:
        self._session = session
        self._client = client

    async def provision(self, user: AuthenticatedUser) -> EmployeeIdentityMapping | None:
        upn = user.preferred_username.casefold().strip() if user.preferred_username else ""
        if not upn:
            return None
        try:
            entra_oid = str(uuid.UUID(user.oid))
        except ValueError as exc:
            raise self._conflict() from exc
        configuration = await self._configuration()
        fields = self._validated_fields(configuration.field_mapping)
        try:
            payload = await self._client.get_entity(
                configuration.entity_name,
                ODataQuery(
                    select=tuple(dict.fromkeys(fields.values())),
                    filter_expression=equals(fields["entraUpn"], upn),
                    top=2,
                ),
            )
        except D365Error as exc:
            structlog.get_logger().warning(
                "identity_auto_provision_d365_failed", error_type=type(exc).__name__
            )
            raise PortalError(
                "IDENTITY_PROVISIONING_UNAVAILABLE",
                "Employee identity verification is temporarily unavailable.",
                503,
            ) from exc

        records = payload.get("value")
        if not isinstance(records, list):
            raise PortalError(
                "IDENTITY_PROVISIONING_UNAVAILABLE",
                "Employee identity verification is temporarily unavailable.",
                503,
            )
        if not records:
            return None
        if len(records) != 1 or not isinstance(records[0], dict):
            raise self._conflict()

        personnel_number, company = self._verify_record(records[0], fields, entra_oid, upn)
        existing = await self._find_conflicts(entra_oid, personnel_number, company)
        if existing:
            if len(existing) == 1 and self._is_same_mapping(
                existing[0], entra_oid, personnel_number, company
            ):
                return existing[0]
            raise self._conflict()

        mapping = EmployeeIdentityMapping(
            id=uuid.uuid4(),
            entra_oid=entra_oid,
            entra_upn=upn,
            entra_email=user.email.casefold() if user.email else None,
            d365_personnel_number=personnel_number,
            d365_company=company,
            mapping_source="d365_oid_auto_verified",
            verified=True,
            enabled=True,
        )
        self._session.add(mapping)
        self._session.add(
            EmployeeIdentityMappingHistory(
                mapping_id=mapping.id,
                changed_by_oid=entra_oid,
                change_type="AUTO_VERIFY_D365_OID",
                after_values={
                    "entra_oid": entra_oid,
                    "d365_personnel_number": personnel_number,
                    "d365_company": company,
                    "mapping_source": mapping.mapping_source,
                },
            )
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            existing = await self._find_conflicts(entra_oid, personnel_number, company)
            if len(existing) == 1 and self._is_same_mapping(
                existing[0], entra_oid, personnel_number, company
            ):
                return existing[0]
            raise self._conflict() from exc
        return mapping

    async def _configuration(self) -> D365EntityMapping:
        configuration = await self._session.scalar(
            select(D365EntityMapping).where(
                D365EntityMapping.mapping_key == "identity",
                D365EntityMapping.enabled.is_(True),
            )
        )
        if configuration is None:
            raise PortalError(
                "IDENTITY_PROVISIONING_NOT_CONFIGURED",
                "Automatic employee identity verification is not configured.",
                503,
            )
        validate_identifier(configuration.entity_name)
        return configuration

    async def _find_conflicts(
        self, entra_oid: str, personnel_number: str, company: str
    ) -> list[EmployeeIdentityMapping]:
        statement = select(EmployeeIdentityMapping).where(
            or_(
                EmployeeIdentityMapping.entra_oid == entra_oid,
                and_(
                    EmployeeIdentityMapping.d365_personnel_number == personnel_number,
                    EmployeeIdentityMapping.d365_company == company,
                ),
            )
        )
        return list((await self._session.scalars(statement)).all())

    @staticmethod
    def _validated_fields(raw: dict[str, Any]) -> dict[str, str]:
        fields = {
            key: validate_identifier(value)
            for key, value in raw.items()
            if key in REQUIRED_IDENTITY_FIELDS and isinstance(value, str)
        }
        if fields.keys() != REQUIRED_IDENTITY_FIELDS:
            raise PortalError(
                "IDENTITY_PROVISIONING_NOT_CONFIGURED",
                "Automatic employee identity mapping is incomplete.",
                503,
            )
        return fields

    @staticmethod
    def _verify_record(
        record: dict[str, Any],
        fields: dict[str, str],
        entra_oid: str,
        upn: str,
    ) -> tuple[str, str]:
        try:
            returned_oid = str(uuid.UUID(str(record.get(fields["entraOid"]))))
        except (TypeError, ValueError, AttributeError) as exc:
            raise IdentityProvisioningService._conflict() from exc
        returned_upn = str(record.get(fields["entraUpn"], "")).casefold().strip()
        if returned_oid != entra_oid or returned_upn != upn:
            raise IdentityProvisioningService._conflict()
        personnel_number = str(record.get(fields["personnelNumber"], "")).strip()
        company = str(record.get(fields["company"], "")).strip()
        if not personnel_number or len(personnel_number) > 64:
            raise IdentityProvisioningService._conflict()
        if not company or len(company) > 32:
            raise IdentityProvisioningService._conflict()
        return personnel_number, company

    @staticmethod
    def _is_same_mapping(
        mapping: EmployeeIdentityMapping,
        entra_oid: str,
        personnel_number: str,
        company: str,
    ) -> bool:
        return (
            mapping.entra_oid == entra_oid
            and mapping.d365_personnel_number == personnel_number
            and (mapping.d365_company or "").casefold() == company.casefold()
            and mapping.enabled
            and mapping.verified
        )

    @staticmethod
    def _conflict() -> PortalError:
        return PortalError(
            "MAPPING_CONFLICT",
            "Your employee identity mapping requires administrator review.",
            409,
        )
