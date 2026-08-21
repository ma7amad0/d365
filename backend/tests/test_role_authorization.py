from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.schemas import AuthenticatedUser
from app.core.exceptions import PortalError, portal_error_handler
from app.employees.router import router


def test_authenticated_user_without_app_role_is_denied() -> None:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(PortalError, portal_error_handler)
    app.state.entra_validator = AsyncMock()
    app.state.entra_validator.validate.return_value = AuthenticatedUser(
        oid="oid-no-role", tid="tenant", roles=frozenset()
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 403
    assert response.json()["error"] == "ROLE_DENIED"
