from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.d365.client import D365Client
from app.d365.exceptions import (
    D365AuthenticationError,
    D365AuthorizationError,
    D365UnavailableError,
)


class FakeTokens:
    def __init__(self) -> None:
        self.calls: list[bool] = []
        self.invalidations = 0

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        self.calls.append(force_refresh)
        return "safe-test-token"

    def invalidate(self) -> None:
        self.invalidations += 1


def client_for(settings: Settings, handler, tokens: FakeTokens | None = None):
    token_service = tokens or FakeTokens()
    http_client = httpx.AsyncClient(
        base_url="https://sssa.operations.dynamics.com/data/",
        transport=httpx.MockTransport(handler),
    )
    return D365Client(settings, token_service, http_client), http_client, token_service


@pytest.mark.asyncio
async def test_401_refreshes_once_then_succeeds(settings: Settings) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401 if attempts == 1 else 200, text="<xml/>", request=request)

    client, http_client, tokens = client_for(settings, handler)
    try:
        response = await client.get_metadata()
        assert response.status_code == 200
        assert tokens.invalidations == 1
        assert tokens.calls == [False, True]
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_repeated_401_is_authentication_error(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request)

    client, http_client, _ = client_for(settings, handler)
    try:
        with pytest.raises(D365AuthenticationError):
            await client.get_metadata()
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_403_is_authorization_error(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, request=request)

    client, http_client, _ = client_for(settings, handler)
    try:
        with pytest.raises(D365AuthorizationError):
            await client.get_metadata()
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_429_retries_using_retry_after(settings: Settings) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            429 if attempts == 1 else 200,
            headers={"Retry-After": "0"},
            text="<xml/>",
            request=request,
        )

    client, http_client, _ = client_for(settings, handler)
    try:
        assert (await client.get_metadata()).status_code == 200
        assert attempts == 2
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_500_exhaustion_is_sanitized(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="sensitive upstream details", request=request)

    client, http_client, _ = client_for(settings, handler)
    try:
        with pytest.raises(D365UnavailableError, match="temporarily unavailable") as error:
            await client.get_metadata()
        assert "sensitive" not in str(error.value)
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_timeout_exhaustion_is_sanitized(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("socket detail", request=request)

    client, http_client, _ = client_for(settings, handler)
    try:
        with pytest.raises(D365UnavailableError, match="bounded retries"):
            await client.get_metadata()
    finally:
        await http_client.aclose()
