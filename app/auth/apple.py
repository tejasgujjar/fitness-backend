from __future__ import annotations

from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.config import get_settings

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        _jwks_client = PyJWKClient(settings.APPLE_JWKS_URL, cache_keys=True)
    return _jwks_client


def verify_apple_identity_token(identity_token: str) -> dict[str, Any]:
    """Verify Apple `identity_token` JWT and return claims (includes `sub`)."""
    settings = get_settings()
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(identity_token)
    payload = jwt.decode(
        identity_token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.APPLE_ISSUER,
        options={"verify_aud": False},
    )
    aud = payload.get("aud")
    auds = [aud] if isinstance(aud, str) else list(aud or [])
    if settings.APPLE_CLIENT_ID not in auds:
        msg = "Invalid audience"
        raise ValueError(msg)
    return payload
