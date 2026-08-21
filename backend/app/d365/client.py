from __future__ import annotations

import asyncio
import email.utils
from datetime import UTC, datetime
from typing import Any, cast

import httpx
import structlog

from app.core.config import Settings
from app.d365.exceptions import (
    D365AuthenticationError,
    D365AuthorizationError,
    D365RateLimitError,
    D365UnavailableError,
)
from app.d365.query import ODataQuery, validate_identifier
from app.d365.token_service import D365TokenService


class D365Client:
    """Async, bounded-retry D365 OData client. Only configured entity names are accepted."""

    def __init__(
        self,
        settings: Settings,
        token_service: D365TokenService,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._tokens = token_service
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=str(settings.D365_ODATA_URL).rstrip("/") + "/",
            timeout=httpx.Timeout(
                connect=settings.D365_CONNECT_TIMEOUT_SECONDS,
                read=settings.D365_READ_TIMEOUT_SECONDS,
                write=10.0,
                pool=5.0,
            ),
            follow_redirects=False,
            headers={"Accept": "application/json", "OData-Version": "4.0"},
        )

    async def __aenter__(self) -> D365Client:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_metadata(self) -> httpx.Response:
        return await self._get("$metadata", accept="application/xml")

    async def get_entity(self, entity: str, query: ODataQuery) -> dict[str, Any]:
        response = await self._get(validate_identifier(entity), params=query.to_params())
        try:
            payload = response.json()
        except ValueError as exc:
            raise D365UnavailableError("D365 returned a malformed JSON response") from exc
        if not isinstance(payload, dict):
            raise D365UnavailableError("D365 returned an unexpected response shape")
        return payload

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        accept: str | None = None,
    ) -> httpx.Response:
        authentication_refreshed = False
        force_refresh_next = False
        last_error: Exception | None = None
        for attempt in range(self._settings.D365_MAX_RETRIES + 1):
            token = await self._tokens.get_access_token(force_refresh=force_refresh_next)
            force_refresh_next = False
            headers = {"Authorization": f"Bearer {token}"}
            if accept:
                headers["Accept"] = accept
            try:
                response = await self._client.get(path, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt >= self._settings.D365_MAX_RETRIES:
                    break
                await asyncio.sleep(min(0.25 * (2**attempt), 4.0))
                continue

            if response.status_code == 401 and not authentication_refreshed:
                self._tokens.invalidate()
                authentication_refreshed = True
                force_refresh_next = True
                continue
            if response.status_code == 401:
                raise D365AuthenticationError("D365 rejected the application credential")
            if response.status_code == 403:
                raise D365AuthorizationError("D365 denied access to the requested resource")
            if response.status_code == 429:
                if attempt >= self._settings.D365_MAX_RETRIES:
                    raise D365RateLimitError("D365 rate limit retry budget was exhausted")
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue
            if response.status_code >= 500:
                if attempt >= self._settings.D365_MAX_RETRIES:
                    raise D365UnavailableError("D365 service is temporarily unavailable")
                await asyncio.sleep(min(0.25 * (2**attempt), 4.0))
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise D365UnavailableError(
                    f"D365 request failed with HTTP {response.status_code}"
                ) from exc
            request_id = response.headers.get("x-ms-request-id") or response.headers.get(
                "request-id"
            )
            structlog.get_logger().info(
                "d365_request_completed",
                status_code=response.status_code,
                d365_request_id=request_id,
            )
            return response
        raise D365UnavailableError("D365 request failed after bounded retries") from last_error

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(max(float(value), 0.0), 30.0)
            except ValueError:
                try:
                    retry_at = cast(datetime, email.utils.parsedate_to_datetime(value))
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=UTC)
                    seconds = float((retry_at - datetime.now(UTC)).total_seconds())
                    return min(max(seconds, 0.0), 30.0)
                except (TypeError, ValueError):
                    pass
        return float(min(0.5 * (2**attempt), 4.0))
