from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    oid: str
    tid: str
    name: str | None = None
    preferred_username: str | None = None
    email: str | None = None
    roles: frozenset[str] = Field(default_factory=frozenset)
    groups: frozenset[str] = Field(default_factory=frozenset)
    scopes: frozenset[str] = Field(default_factory=frozenset)
    client_id: str | None = None


class MeResponse(BaseModel):
    oid: str
    name: str | None
    username: str | None
    roles: list[str]
    mapping_status: str
