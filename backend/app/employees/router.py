from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.dependencies import require_roles
from app.auth.schemas import AuthenticatedUser, MeResponse
from app.core.exceptions import PortalError
from app.d365.leave_service import D365LeaveService
from app.d365.profile_service import D365ProfileService
from app.database.models import EmployeeIdentityMapping
from app.database.session import get_session
from app.employees.mapping_service import IdentityMappingService
from app.employees.provisioning_service import IdentityProvisioningService
from app.employees.schemas import EmployeeProfileResponse, LeaveBalancesResponse

router = APIRouter(prefix="/api/v1", tags=["employee"])
portal_user = require_roles("employee", "manager", "hr", "finance", "portal_admin", "auditor")


async def resolve_identity(
    request: Request,
    user: AuthenticatedUser,
    session: AsyncSession,
    *,
    required: bool,
) -> EmployeeIdentityMapping | None:
    mapping = await IdentityMappingService(session).find_verified(user.oid)
    if mapping is None:
        mapping = await IdentityProvisioningService(
            session, request.app.state.d365_client
        ).provision(user)
        if mapping is not None:
            await record_audit(
                session,
                request,
                user,
                action="IDENTITY_AUTO_PROVISION",
                resource="employee_identity_mapping",
                result="SUCCESS",
                target_employee=mapping.d365_personnel_number,
                details={"source": "d365_oid_auto_verified"},
            )
    if mapping is None and required:
        raise PortalError(
            "MAPPING_REQUIRED",
            "No D365 employee matched your verified Entra identity.",
            403,
        )
    return mapping


@router.get("/me", response_model=MeResponse)
async def me(
    request: Request,
    user: AuthenticatedUser = Depends(portal_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    mapping = await resolve_identity(request, user, session, required=False)
    await record_audit(
        session,
        request,
        user,
        action="PROFILE_VIEW",
        resource="/api/v1/me",
        result="SUCCESS",
        target_employee=mapping.d365_personnel_number if mapping else None,
    )
    return MeResponse(
        oid=user.oid,
        name=user.name,
        username=user.preferred_username,
        roles=sorted(user.roles),
        mapping_status="verified" if mapping else "unmapped",
    )


@router.get("/me/profile", response_model=EmployeeProfileResponse)
async def my_profile(
    request: Request,
    user: AuthenticatedUser = Depends(portal_user),
    session: AsyncSession = Depends(get_session),
) -> EmployeeProfileResponse:
    mapping = await resolve_identity(request, user, session, required=True)
    assert mapping is not None
    profile = await D365ProfileService(session, request.app.state.d365_client).get_profile(mapping)
    await record_audit(
        session,
        request,
        user,
        action="PROFILE_VIEW",
        resource="/api/v1/me/profile",
        result="SUCCESS",
        target_employee=mapping.d365_personnel_number,
    )
    return profile


@router.get("/me/leave-balances", response_model=LeaveBalancesResponse)
async def my_leave_balances(
    request: Request,
    user: AuthenticatedUser = Depends(portal_user),
    session: AsyncSession = Depends(get_session),
) -> LeaveBalancesResponse:
    mapping = await resolve_identity(request, user, session, required=True)
    assert mapping is not None
    balances = await D365LeaveService(session, request.app.state.d365_client).get_balances(mapping)
    await record_audit(
        session,
        request,
        user,
        action="LEAVE_BALANCE_VIEW",
        resource="/api/v1/me/leave-balances",
        result="SUCCESS",
        target_employee=mapping.d365_personnel_number,
    )
    return balances
