from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AppleAuthRequest(BaseModel):
    identity_token: str
    authorization_code: str | None = None
    email: str | None = None
    user: str | None = Field(
        default=None,
        description="Apple one-time user identifier on first sign-in (optional)",
    )


class RefreshRequest(BaseModel):
    refresh_token: str


class DevAuthRequest(BaseModel):
    """Local testing only: fake Apple `sub` and optional email."""

    apple_user_id: str = Field(
        ...,
        description="Stable fake Apple subject, e.g. dev-postman-1",
    )
    email: str | None = None


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
