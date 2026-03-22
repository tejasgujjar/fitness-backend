from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_auth_apple_creates_user(client):
    with patch("app.api.routes.auth.verify_apple_identity_token") as v:
        v.return_value = {"sub": "apple-test-user-1", "email": "test@example.com"}
        r = await client.post(
            "/auth/apple",
            json={"identity_token": "dummy-token"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
