from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.core.config import Settings
from app.models.user import User

router = APIRouter()


def _parse_dotenv_file(env_path: Path) -> dict[str, str]:
    """
    Minimal `.env` parser for `KEY=VALUE` pairs.

    We only care about `APP_FLAG_*` keys, so this intentionally avoids supporting
    advanced dotenv features (variable interpolation, multiline values, etc.).
    """

    try:
        raw = env_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}

    out: dict[str, str] = {}
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[len("export ") :].lstrip()

        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if not k.startswith("APP_FLAG_"):
            continue

        v = v.strip()
        if len(v) >= 2 and ((v[0] == v[-1]) and v[0] in ("'", '"')):
            v = v[1:-1]

        out[k] = v

    return out


@router.get("/app-flags", response_model=dict[str, str])
async def read_app_flags(
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    flags = {k: v for k, v in os.environ.items() if k.startswith("APP_FLAG_")}

    # Local dev convenience: if flags are declared in `.env` but aren't present
    # in this process environment, fall back to reading `.env` directly.
    dotenv_flags = _parse_dotenv_file(Path(".env"))
    for k, v in dotenv_flags.items():
        flags.setdefault(k, v)

    # User-scoped overrides for specific flags.
    # Currently only `APP_FLAG_ENABLE_DEVELOPER_MODE` is user-eligible via allowlist.
    key = "APP_FLAG_ENABLE_DEVELOPER_MODE"
    if key in flags:
        # Avoid `get_settings()` caching issues: auth (JWT decode) uses cached
        # settings, while flag eligibility should reflect current `.env`/env.
        allow_raw = Settings().DEVELOPER_MODE_ENABLED_USER_EMAILS
        allowlist = {e.strip().lower() for e in allow_raw.split(",") if e.strip()}
        user_email = (_current_user.email or "").strip().lower()
        if user_email not in allowlist:
            flags[key] = "false"

    return flags

