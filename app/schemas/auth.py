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


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
