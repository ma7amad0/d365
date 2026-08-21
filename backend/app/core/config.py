from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Validated process configuration; secrets are never represented as plain text."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_NAME: str = "SSSA Employee Portal"
    LOG_LEVEL: str = "INFO"
    API_DOCS_ENABLED: bool = True

    TENANT_ID: str = ""
    PORTAL_CLIENT_ID: str = ""
    PORTAL_API_AUDIENCE: str = ""

    D365_CLIENT_ID: str = ""
    D365_CLIENT_SECRET: SecretStr = SecretStr("")
    D365_BASE_URL: AnyHttpUrl = AnyHttpUrl("https://sssa.operations.dynamics.com")
    D365_ODATA_URL: AnyHttpUrl = AnyHttpUrl("https://sssa.operations.dynamics.com/data")
    D365_TOKEN_AUTH_MODE: Literal["secret", "certificate"] = "secret"

    DATABASE_URL: str = "postgresql+asyncpg://portal:password@postgres/employee_portal"
    REDIS_URL: str = "redis://redis:6379/0"
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"]
    )
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost"]
    )
    FRONTEND_URL: str = "http://localhost"
    SESSION_SECRET: SecretStr = SecretStr("")

    D365_CONNECT_TIMEOUT_SECONDS: float = 5.0
    D365_READ_TIMEOUT_SECONDS: float = 30.0
    D365_MAX_RETRIES: int = 3
    D365_METADATA_CACHE_SECONDS: int = 21_600
    D365_METADATA_MAX_BYTES: int = Field(default=268_435_456, ge=1_048_576, le=536_870_912)

    @field_validator("ALLOWED_HOSTS", "CORS_ORIGINS", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_security_settings(self) -> Settings:
        if self.APP_ENV == "production":
            missing = []
            for field in ("TENANT_ID", "PORTAL_CLIENT_ID", "PORTAL_API_AUDIENCE", "D365_CLIENT_ID"):
                if not getattr(self, field):
                    missing.append(field)
            if (
                self.D365_TOKEN_AUTH_MODE == "secret"
                and not self.D365_CLIENT_SECRET.get_secret_value()
            ):
                missing.append("D365_CLIENT_SECRET")
            if len(self.SESSION_SECRET.get_secret_value()) < 32:
                missing.append("SESSION_SECRET (minimum 32 characters)")
            if any(origin == "*" for origin in self.CORS_ORIGINS):
                raise ValueError("CORS_ORIGINS cannot contain '*' in production")
            if missing:
                raise ValueError(f"Missing required production settings: {', '.join(missing)}")
        return self

    @property
    def d365_scope(self) -> list[str]:
        return [f"{str(self.D365_BASE_URL).rstrip('/')}/.default"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
