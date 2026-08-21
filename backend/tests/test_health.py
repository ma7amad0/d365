from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.health.router import router


class Readiness:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def check(self) -> dict[str, str]:
        return {"database": "ok", "redis": "ok" if self.ready else "unavailable"}


def make_client(ready: bool = True) -> TestClient:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.readiness = Readiness(ready)
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return TestClient(app)


def test_liveness() -> None:
    with make_client() as client:
        assert client.get("/health/live").json() == {"status": "ok", "dependencies": None}


def test_readiness_returns_503_for_dependency_failure() -> None:
    with make_client(False) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
