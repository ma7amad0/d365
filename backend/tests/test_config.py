import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="cannot contain"):
        Settings(
            APP_ENV="production",
            TENANT_ID="tenant",
            PORTAL_CLIENT_ID="portal",
            PORTAL_API_AUDIENCE="audience",
            D365_CLIENT_ID="d365",
            D365_CLIENT_SECRET="secret",
            SESSION_SECRET="x" * 32,
            CORS_ORIGINS=["*"],
        )


def test_production_requires_security_configuration() -> None:
    with pytest.raises(ValidationError, match="Missing required"):
        Settings(APP_ENV="production")


def test_d365_scope_has_no_duplicate_slash(settings: Settings) -> None:
    assert settings.d365_scope == ["https://sssa.operations.dynamics.com/.default"]
