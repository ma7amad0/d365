from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    dependencies: dict[str, str] | None = None


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
async def ready(request: Request, response: Response) -> HealthResponse:
    checks = await request.app.state.readiness.check()
    is_ready = all(value == "ok" for value in checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="ready" if is_ready else "not_ready", dependencies=checks)
