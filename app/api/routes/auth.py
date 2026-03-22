from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.apple import verify_apple_identity_token
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.user import User
from app.core.time import UTC
from app.schemas.auth import AppleAuthRequest, AuthTokensResponse, RefreshRequest

router = APIRouter()


@router.post("/apple", response_model=AuthTokensResponse)
async def auth_apple(
    body: AppleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthTokensResponse:
    try:
        claims = verify_apple_identity_token(body.identity_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Apple identity token: {e!s}",
        ) from e

    apple_sub = str(claims["sub"])
    email = body.email or claims.get("email")

    result = await db.execute(select(User).where(User.apple_user_id == apple_sub))
    user = result.scalar_one_or_none()
    now = datetime.now(UTC)

    if user is None:
        user = User(
            apple_user_id=apple_sub,
            email=email,
            created_at=now,
            last_sync_at=None,
        )
        db.add(user)
        await db.flush()
    elif email and user.email != email:
        user.email = email

    return AuthTokensResponse(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
        user_id=user.id,
    )


@router.post("/refresh", response_model=AuthTokensResponse)
async def auth_refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthTokensResponse:
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        uid = UUID(str(payload["sub"]))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return AuthTokensResponse(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
        user_id=user.id,
    )
