from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, urlparse, urlunparse

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_query_params(url: str, keys: set[str]) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    for k in keys:
        qs.pop(k, None)
    from urllib.parse import urlencode

    new_query = urlencode({k: v[0] for k, v in qs.items()}) if qs else ""
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def _async_database_url(url: str) -> str:
    u = url.strip()
    if u.startswith("postgres://"):
        u = u.replace("postgres://", "postgresql://", 1)
    if u.startswith("postgresql://"):
        u = u.replace("postgresql://", "postgresql+asyncpg://", 1)
    return u


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/fitness",
    )
    JWT_SECRET: str = Field(
        default="dev-insecure-change-me-use-at-least-32-characters",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    APPLE_CLIENT_ID: str = Field(default="com.example.app")
    APPLE_ISSUER: str = "https://appleid.apple.com"
    APPLE_JWKS_URL: str = "https://appleid.apple.com/auth/keys"
    ENV: str = "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_sqlalchemy_database_uri(self) -> str:
        return _async_database_url(self.DATABASE_URL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def asyncpg_connect_args(self) -> dict:
        """Railway / cloud Postgres often pass sslmode=require in the URL."""
        parsed = urlparse(self.async_sqlalchemy_database_uri)
        qs = parse_qs(parsed.query)
        sslmode = (qs.get("sslmode") or ["prefer"])[0]
        args: dict = {}
        if sslmode in ("require", "verify-ca", "verify-full"):
            args["ssl"] = True
        return args

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_sqlalchemy_database_uri_clean(self) -> str:
        """URL without sslmode (asyncpg uses connect_args ssl instead)."""
        return _strip_query_params(
            self.async_sqlalchemy_database_uri,
            {"sslmode"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
