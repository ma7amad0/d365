import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        APP_ENV="test",
        TENANT_ID="11111111-1111-1111-1111-111111111111",
        D365_CLIENT_ID="22222222-2222-2222-2222-222222222222",
        D365_CLIENT_SECRET="unit-test-secret",
        D365_MAX_RETRIES=1,
    )
