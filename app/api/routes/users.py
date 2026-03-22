from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import MeResponse

router = APIRouter()


@router.get("/me", response_model=MeResponse, response_model_by_alias=True)
async def read_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        apple_user_id=current_user.apple_user_id,
        created_at=current_user.created_at,
        last_sync_at=current_user.last_sync_at,
    )
