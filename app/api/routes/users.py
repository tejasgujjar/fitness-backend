from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user
from app.models.account_deletion_history import AccountDeletionHistory
from app.models.diet_log import DietLog
from app.models.user import User
from app.models.workout_log import WorkoutLog
from app.schemas.user import DeleteAccountRequest, MeResponse

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


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    body: DeleteAccountRequest | None = None,
) -> Response:
    workout_count = await db.scalar(
        select(func.count()).select_from(WorkoutLog).where(WorkoutLog.user_id == current_user.id),
    )
    diet_count = await db.scalar(
        select(func.count()).select_from(DietLog).where(DietLog.user_id == current_user.id),
    )

    payload = body or DeleteAccountRequest()
    history = AccountDeletionHistory(
        user_id=current_user.id,
        email=current_user.email,
        apple_user_id=current_user.apple_user_id,
        trigger=payload.trigger or "self_service",
        workout_logs_deleted_count=workout_count or 0,
        diet_logs_deleted_count=diet_count or 0,
        app_version=payload.app_version,
        device_id=payload.device_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(history)

    await db.delete(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
