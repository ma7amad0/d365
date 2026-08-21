from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt
from jwt import InvalidTokenError, PyJWK

from app.auth.schemas import AuthenticatedUser
from app.core.config import Settings
from app.core.exceptions import PortalError


class EntraTokenValidator:
    """Validate tenant-scoped Entra v2 access tokens using cached OIDC signing keys."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=False
        )
        self._lock = asyncio.Lock()
        self._keys: dict[str, PyJWK] = {}
        self._expires_at = 0.0

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def validate(self, token: str) -> AuthenticatedUser:
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise self._invalid() from exc
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise self._invalid()

        key = await self._get_key(str(header["kid"]))
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key.key,
                algorithms=["RS256"],
                audience=self._settings.PORTAL_API_AUDIENCE,
                issuer=self._settings.entra_issuer,
                options={
                    "require": ["exp", "iat", "iss", "aud", "tid", "oid", "ver"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
                leeway=60,
            )
        except InvalidTokenError as exc:
            raise self._invalid() from exc

        if claims.get("tid") != self._settings.TENANT_ID:
            raise self._invalid()
        if claims.get("ver") != self._settings.ENTRA_ACCEPTED_TOKEN_VERSION:
            raise self._invalid()

        client_id = claims.get("azp") or claims.get("appid")
        allowed_clients = self._settings.PORTAL_ALLOWED_CLIENT_IDS
        if allowed_clients and client_id not in allowed_clients:
            raise PortalError("CLIENT_NOT_ALLOWED", "The calling application is not allowed.", 403)
        scopes = self._scope_set(claims.get("scp"))
        if self._settings.PORTAL_REQUIRED_SCOPE not in scopes:
            raise PortalError("SCOPE_DENIED", "The token does not grant portal API access.", 403)

        oid = claims.get("oid")
        if not isinstance(oid, str) or not oid:
            raise self._invalid()
        return AuthenticatedUser(
            oid=oid,
            tid=str(claims["tid"]),
            name=self._optional_string(claims.get("name")),
            preferred_username=self._optional_string(
                claims.get("preferred_username") or claims.get("upn")
            ),
            email=self._optional_string(claims.get("email")),
            roles=self._string_set(claims.get("roles")),
            groups=self._string_set(claims.get("groups")),
            scopes=scopes,
            client_id=self._optional_string(client_id),
        )

    async def _get_key(self, kid: str) -> PyJWK:
        expired = time.monotonic() >= self._expires_at
        if expired or kid not in self._keys:
            await self._refresh_keys(force=not expired and kid not in self._keys)
        key = self._keys.get(kid)
        if key is None:
            raise self._invalid()
        return key

    async def _refresh_keys(self, *, force: bool = False) -> None:
        async with self._lock:
            if not force and time.monotonic() < self._expires_at and self._keys:
                return
            try:
                discovery_response = await self._client.get(self._settings.entra_discovery_url)
                discovery_response.raise_for_status()
                discovery = discovery_response.json()
                if discovery.get("issuer") != self._settings.entra_issuer:
                    raise ValueError("issuer mismatch")
                jwks_uri = str(discovery["jwks_uri"])
                parsed = urlparse(jwks_uri)
                if parsed.scheme != "https" or parsed.hostname != "login.microsoftonline.com":
                    raise ValueError("untrusted JWKS URI")
                keys_response = await self._client.get(jwks_uri)
                keys_response.raise_for_status()
                raw_keys = keys_response.json().get("keys", [])
                keys = {
                    str(item["kid"]): PyJWK.from_dict(item)
                    for item in raw_keys
                    if item.get("kty") == "RSA"
                    and item.get("use") == "sig"
                    and item.get("alg", "RS256") == "RS256"
                    and isinstance(item.get("kid"), str)
                }
                if not keys:
                    raise ValueError("no signing keys")
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise PortalError(
                    "IDENTITY_PROVIDER_UNAVAILABLE",
                    "Sign-in validation is temporarily unavailable.",
                    503,
                ) from exc
            self._keys = keys
            self._expires_at = time.monotonic() + self._settings.ENTRA_METADATA_CACHE_SECONDS

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _string_set(value: object) -> frozenset[str]:
        if not isinstance(value, list):
            return frozenset()
        return frozenset(item for item in value if isinstance(item, str))

    @staticmethod
    def _scope_set(value: object) -> frozenset[str]:
        if not isinstance(value, str):
            return frozenset()
        return frozenset(value.split())

    @staticmethod
    def _invalid() -> PortalError:
        return PortalError("INVALID_TOKEN", "Authentication token validation failed.", 401)
