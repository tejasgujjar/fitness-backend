from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import RequestAudit


def _clear_app_flag_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in list(os.environ.keys()):
        if k.startswith("APP_FLAG_"):
            monkeypatch.delenv(k, raising=False)


def _set_empty_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # Keep `.env` parsing deterministic by switching the CWD and writing a minimal file.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("# empty\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_app_flags_requires_auth(client):
    r = await client.get("/api/app-flags")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_app_flags_returns_env_vars(monkeypatch, client, auth_headers, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("# empty\n", encoding="utf-8")
    _clear_app_flag_env(monkeypatch)

    monkeypatch.setenv("APP_FLAG_A", "foo")
    monkeypatch.setenv("APP_FLAG_B", "bar")

    r = await client.get("/api/app-flags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"APP_FLAG_A": "foo", "APP_FLAG_B": "bar"}


@pytest.mark.asyncio
async def test_app_flags_falls_back_to_dotenv(
    monkeypatch, client, auth_headers, tmp_path
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "APP_FLAG_FROM_DOTENV=abc\n",
        encoding="utf-8",
    )
    _clear_app_flag_env(monkeypatch)

    r = await client.get("/api/app-flags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"APP_FLAG_FROM_DOTENV": "abc"}


@pytest.mark.asyncio
async def test_app_flags_excluded_from_audit_persistence(client, engine, auth_headers):
    r = await client.get("/api/app-flags", headers=auth_headers)
    assert r.status_code == 200

    rid = r.headers.get("x-request-id")
    assert rid

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        row = (
            await session.execute(select(RequestAudit).where(RequestAudit.request_id == UUID(rid)))
        ).scalar_one_or_none()

    assert row is None


@pytest.mark.asyncio
async def test_app_flags_developer_mode_eligible(
    monkeypatch, client, auth_headers, tmp_path
):
    _set_empty_env(monkeypatch, tmp_path)
    _clear_app_flag_env(monkeypatch)
    monkeypatch.setenv("DEVELOPER_MODE_ENABLED_USER_EMAILS", "test@example.com")
    monkeypatch.setenv("APP_FLAG_ENABLE_DEVELOPER_MODE", "true")

    r = await client.get("/api/app-flags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"APP_FLAG_ENABLE_DEVELOPER_MODE": "true"}


@pytest.mark.asyncio
async def test_app_flags_developer_mode_ineligible(
    monkeypatch, client, auth_headers, tmp_path
):
    _set_empty_env(monkeypatch, tmp_path)
    _clear_app_flag_env(monkeypatch)
    monkeypatch.setenv(
        "DEVELOPER_MODE_ENABLED_USER_EMAILS",
        "other@example.com",
    )
    monkeypatch.setenv("APP_FLAG_ENABLE_DEVELOPER_MODE", "true")

    r = await client.get("/api/app-flags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"APP_FLAG_ENABLE_DEVELOPER_MODE": "false"}

