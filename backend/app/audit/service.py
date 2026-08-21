from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import AuthenticatedUser
from app.database.models import AuditEvent


async def record_audit(
    session: AsyncSession,
    request: Request,
    user: AuthenticatedUser,
    *,
    action: str,
    resource: str,
    result: str,
    target_employee: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    client_ip = request.client.host if request.client else None
    session.add(
        AuditEvent(
            entra_oid=user.oid,
            user_upn=user.preferred_username,
            action=action,
            resource=resource,
            target_employee=target_employee,
            client_ip=client_ip,
            user_agent=request.headers.get("User-Agent", "")[:512] or None,
            result=result,
            correlation_id=getattr(request.state, "request_id", "unavailable"),
            details=details,
        )
    )
    await session.commit()
