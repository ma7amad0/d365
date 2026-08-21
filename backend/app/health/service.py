from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.database.session import database_is_ready


class ReadinessService:
    """Check local dependencies without letting external outages drain application pods."""

    def __init__(self, engine: AsyncEngine, redis: Redis) -> None:
        self._engine = engine
        self._redis = redis

    async def check(self) -> dict[str, str]:
        database = await database_is_ready(self._engine)
        try:
            redis_ready = bool(await self._redis.ping())
        except Exception:
            redis_ready = False
        return {
            "database": "ok" if database else "unavailable",
            "redis": "ok" if redis_ready else "unavailable",
        }
