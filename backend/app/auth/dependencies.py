from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.schemas import AuthenticatedUser
from app.core.exceptions import PortalError

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise PortalError("AUTHENTICATION_REQUIRED", "Authentication is required.", 401)
    if len(credentials.credentials) > 16_384:
        raise PortalError("INVALID_TOKEN", "Authentication token validation failed.", 401)
    user = cast(
        AuthenticatedUser,
        await request.app.state.entra_validator.validate(credentials.credentials),
    )
    structlog.contextvars.bind_contextvars(user_oid=user.oid)
    return user


def require_roles(*required: str) -> Callable[..., Awaitable[AuthenticatedUser]]:
    async def dependency(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not user.roles.intersection(required):
            structlog.get_logger().warning(
                "role_denied", required_roles=sorted(required), user_oid=user.oid
            )
            raise PortalError("ROLE_DENIED", "You are not authorized for this resource.", 403)
        return user

    return dependency
