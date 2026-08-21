from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import msal
import structlog

from app.core.config import Settings
from app.d365.exceptions import D365AuthenticationError


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str
    expires_at: float


class D365TokenService:
    """Acquires and caches app-only tokens without exposing token material to callers' logs."""

    _REFRESH_SKEW_SECONDS = 300

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._token: AccessToken | None = None
        self._msal_cache = msal.SerializableTokenCache()
        self._application = self._build_application()

    def _build_application(self) -> msal.ConfidentialClientApplication:
        if self._settings.D365_TOKEN_AUTH_MODE != "secret":
            raise D365AuthenticationError(
                "Certificate authentication is selected but certificate settings are not configured"
            )
        secret = self._settings.D365_CLIENT_SECRET.get_secret_value()
        if not self._settings.TENANT_ID or not self._settings.D365_CLIENT_ID or not secret:
            raise D365AuthenticationError("D365 client credential settings are incomplete")
        return msal.ConfidentialClientApplication(
            client_id=self._settings.D365_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{self._settings.TENANT_ID}",
            client_credential=secret,
            token_cache=self._msal_cache,
        )

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        now = time.time()
        if (
            not force_refresh
            and self._token is not None
            and self._token.expires_at - self._REFRESH_SKEW_SECONDS > now
        ):
            return self._token.value

        async with self._lock:
            now = time.time()
            if (
                not force_refresh
                and self._token is not None
                and self._token.expires_at - self._REFRESH_SKEW_SECONDS > now
            ):
                return self._token.value
            result: dict[str, Any] = await asyncio.to_thread(
                self._application.acquire_token_for_client,
                scopes=self._settings.d365_scope,
            )
            token = result.get("access_token")
            if not isinstance(token, str):
                error_code = str(result.get("error", "authentication_failed"))
                correlation_id = str(result.get("correlation_id", "unavailable"))
                structlog.get_logger().error(
                    "d365_token_acquisition_failed",
                    error_code=error_code,
                    correlation_id=correlation_id,
                )
                raise D365AuthenticationError(
                    "D365 token acquisition failed "
                    f"({error_code}); correlation ID: {correlation_id}"
                )
            expires_in = max(int(result.get("expires_in", 3600)), 60)
            self._token = AccessToken(value=token, expires_at=now + expires_in)
            return token

    def invalidate(self) -> None:
        self._token = None
