from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, urlparse, urlunparse

from pydantic import AliasChoices, Field, computed_field, model_validator
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
        default="postgresql+asyncpg://postgres@localhost:5432/fitness",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL"),
        description=(
            "Postgres connection URL. Default uses role `postgres` (common locally). "
            "Set in .env to match your install (e.g. user, password, db name)."
        ),
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
    RAILWAY_ENVIRONMENT: str | None = Field(
        default=None,
        description="Set automatically by Railway runtime.",
    )
    ALLOW_DEV_AUTH: bool = Field(
        default=False,
        description="If true and ENV is development, POST /auth/dev is allowed (never enable in production).",
    )
    DEV_AUTH_SECRET: str | None = Field(
        default=None,
        description="If set, POST /auth/dev requires header X-Dev-Auth with this value.",
    )

    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key for Responses API / Agent calls.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Model ID for Responses API when creating a response.",
    )
    OPENAI_AGENT_ID: str | None = Field(
        default=None,
        description=(
            "Optional Agent Builder / workflow id merged into Responses API "
            "requests as extra_body (see agent_parser)."
        ),
    )
    OPENAI_TIMEOUT_SECONDS: float = Field(
        default=120.0,
        description="Timeout for OpenAI Responses API calls.",
    )

    AUDIT_MAX_BODY_BYTES: int = Field(
        default=65536,
        description="Max bytes stored per request/response body in request_audits (truncated beyond this).",
    )
    AUDIT_EXCLUDED_PATH_PREFIXES: str = Field(
        default="/health,/docs,/openapi.json,/redoc",
        description=(
            "Comma-separated URL path prefixes that skip persistence to request_audits. "
            "Set to empty string to audit all routes."
        ),
    )

    @model_validator(mode="after")
    def _validate_db_url_for_env(self) -> "Settings":
        # Avoid accidental localhost fallback in hosted environments.
        db_url = self.DATABASE_URL.strip().lower()
        is_local_db = "localhost" in db_url or "127.0.0.1" in db_url or "@/" in db_url
        is_hosted_runtime = self.ENV != "development" or bool(self.RAILWAY_ENVIRONMENT)
        if is_hosted_runtime and is_local_db:
            raise ValueError(
                "DATABASE_URL points to local Postgres in hosted runtime. "
                "Set Railway service env var DATABASE_URL (or POSTGRES_URL) to your managed Postgres URL."
            )
        return self

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

    def audit_excluded_path_prefixes(self) -> list[str]:
        raw = self.AUDIT_EXCLUDED_PATH_PREFIXES.strip()
        if not raw:
            return []
        return [p.strip() for p in raw.split(",") if p.strip()]

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


def is_dev_auth_allowed() -> bool:
    """POST /auth/dev only when explicitly enabled and ENV is development."""
    s = get_settings()
    return bool(s.ALLOW_DEV_AUTH and s.ENV == "development")
