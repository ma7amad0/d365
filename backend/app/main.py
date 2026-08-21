from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from redis.asyncio import Redis

from app.auth.service import EntraTokenValidator
from app.core.config import get_settings
from app.core.exceptions import PortalError, portal_error_handler
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.d365.client import D365Client
from app.d365.token_service import D365TokenService
from app.database.session import create_engine, create_session_factory
from app.employees.router import router as employees_router
from app.health.router import router as health_router
from app.health.service import ReadinessService

settings = get_settings()
configure_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(settings)
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.redis = redis
    app.state.readiness = ReadinessService(engine, redis)
    app.state.entra_validator = EntraTokenValidator(settings)
    app.state.d365_client = D365Client(settings, D365TokenService(settings))
    yield
    await app.state.entra_validator.close()
    await app.state.d365_client.close()
    await redis.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.API_DOCS_ENABLED else None,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
)
app.include_router(health_router)
app.include_router(employees_router)
app.add_exception_handler(PortalError, portal_error_handler)
