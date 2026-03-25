from __future__ import annotations

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_auth_dev_disabled_returns_404(client, monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH", "false")
    monkeypatch.setenv("ENV", "development")
    get_settings.cache_clear()

    r = await client.post(
        "/auth/dev",
        json={"apple_user_id": "dev-1"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_auth_dev_disabled_when_env_not_development(client, monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH", "true")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@db.example.com:5432/fitness",
    )
    get_settings.cache_clear()

    r = await client.post(
        "/auth/dev",
        json={"apple_user_id": "dev-1"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_auth_dev_enabled_returns_tokens_and_me(client, monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH", "true")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("DEV_AUTH_SECRET", raising=False)
    get_settings.cache_clear()

    r = await client.post(
        "/auth/dev",
        json={"apple_user_id": "dev-postman-1", "email": "a@example.com"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data

    token = data["access_token"]
    r2 = await client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    me = r2.json()
    assert me["appleUserId"] == "dev-postman-1"
    assert me["email"] == "a@example.com"


@pytest.mark.asyncio
async def test_auth_dev_requires_secret_header_when_configured(client, monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH", "true")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("DEV_AUTH_SECRET", "test-secret-123")
    get_settings.cache_clear()

    r = await client.post(
        "/auth/dev",
        json={"apple_user_id": "dev-2"},
    )
    assert r.status_code == 401

    r2 = await client.post(
        "/auth/dev",
        json={"apple_user_id": "dev-2"},
        headers={"X-Dev-Auth": "test-secret-123"},
    )
    assert r2.status_code == 200
