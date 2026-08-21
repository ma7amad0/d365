from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PortalError
from app.database.models import EmployeeIdentityMapping


class IdentityMappingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_verified(self, entra_oid: str) -> EmployeeIdentityMapping | None:
        statement = select(EmployeeIdentityMapping).where(
            EmployeeIdentityMapping.entra_oid == entra_oid,
            EmployeeIdentityMapping.enabled.is_(True),
            EmployeeIdentityMapping.verified.is_(True),
        )
        mappings = list((await self._session.scalars(statement)).all())
        if len(mappings) > 1:
            raise PortalError(
                "MAPPING_CONFLICT",
                "Your employee identity mapping requires administrator review.",
                409,
            )
        return mappings[0] if mappings else None

    async def require_verified(self, entra_oid: str) -> EmployeeIdentityMapping:
        mapping = await self.find_verified(entra_oid)
        if mapping is None:
            raise PortalError(
                "MAPPING_REQUIRED",
                "Your employee identity has not been verified by a portal administrator.",
                403,
            )
        return mapping
