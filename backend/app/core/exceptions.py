from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class PortalError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def portal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, PortalError):
        raise exc
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "error": exc.code,
            "message": exc.message,
            "requestId": getattr(request.state, "request_id", "unavailable"),
        },
    )
