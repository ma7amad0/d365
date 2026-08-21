from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.service import EntraTokenValidator
from app.core.config import Settings
from app.core.exceptions import PortalError

KID = "unit-test-key"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(
    PRIVATE_KEY.public_key(), as_dict=True
)
PUBLIC_JWK.update({"kid": KID, "use": "sig", "alg": "RS256"})


def token(settings: Settings, **overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": settings.entra_issuer,
        "aud": settings.PORTAL_API_AUDIENCE,
        "tid": settings.TENANT_ID,
        "oid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "iat": now,
        "nbf": now - 1,
        "exp": now + 300,
        "ver": "2.0",
        "azp": settings.PORTAL_CLIENT_ID,
        "name": "Test Employee",
        "preferred_username": "employee@example.test",
        "roles": ["employee"],
        "scp": "access_as_user",
    }
    claims.update(overrides)
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})


def validator(settings: Settings) -> tuple[EntraTokenValidator, httpx.AsyncClient]:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": settings.entra_issuer,
                    "jwks_uri": "https://login.microsoftonline.com/test/discovery/v2.0/keys",
                },
            )
        return httpx.Response(200, json={"keys": [PUBLIC_JWK]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return EntraTokenValidator(settings, client), client


@pytest.mark.asyncio
async def test_valid_token_returns_allow_listed_claims(settings: Settings) -> None:
    service, client = validator(settings)
    try:
        user = await service.validate(token(settings))
        assert user.oid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert user.roles == frozenset({"employee"})
        assert user.preferred_username == "employee@example.test"
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("tid", "wrong-tenant"),
        ("iss", "https://login.microsoftonline.com/wrong/v2.0"),
        ("aud", "api://another-api"),
        ("ver", "1.0"),
        ("exp", 1),
    ],
)
async def test_invalid_security_claims_are_rejected(
    settings: Settings, claim: str, value: object
) -> None:
    service, client = validator(settings)
    try:
        with pytest.raises(PortalError) as error:
            await service.validate(token(settings, **{claim: value}))
        assert error.value.code == "INVALID_TOKEN"
        assert error.value.status_code == 401
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_unapproved_calling_client_is_rejected(settings: Settings) -> None:
    service, client = validator(settings)
    try:
        with pytest.raises(PortalError) as error:
            await service.validate(token(settings, azp="unapproved-client"))
        assert error.value.code == "CLIENT_NOT_ALLOWED"
        assert error.value.status_code == 403
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_missing_delegated_scope_is_rejected(settings: Settings) -> None:
    service, client = validator(settings)
    try:
        with pytest.raises(PortalError) as error:
            await service.validate(token(settings, scp="other_scope"))
        assert error.value.code == "SCOPE_DENIED"
        assert error.value.status_code == 403
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_untrusted_jwks_uri_is_rejected(settings: Settings) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"issuer": settings.entra_issuer, "jwks_uri": "https://evil.test/keys"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = EntraTokenValidator(settings, client)
    try:
        with pytest.raises(PortalError) as error:
            await service.validate(token(settings))
        assert error.value.code == "IDENTITY_PROVIDER_UNAVAILABLE"
    finally:
        await client.aclose()
