from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import UTC
from app.db.session import get_db
from app.deps import get_current_user
from app.models.diet_log import DietLog
from app.models.user import User
from app.models.workout_log import WorkoutLog
from app.schemas.diet import DietRead
from app.schemas.sync import (
    SyncItemResult,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
)
from app.schemas.workout import WorkoutRead
from app.services.sync import now_utc, process_sync_item

router = APIRouter()


@router.post("/push", response_model=SyncPushResponse)
async def sync_push(
    body: SyncPushRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SyncPushResponse:
    now = now_utc()
    results: list[SyncItemResult] = []
    mappings: dict[str, str] = {}

    for item in body.items:
        res, server_id = await process_sync_item(db, user, item, now)
        results.append(res)
        if item.operation == "create" and res.ok and server_id is not None:
            mappings[str(item.local_id)] = str(server_id)

    user.last_sync_at = datetime.now(UTC)

    return SyncPushResponse(mappings=mappings, results=results)


@router.get("/pull", response_model=SyncPullResponse)
async def sync_pull(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    since: datetime | None = Query(
        None,
        description="Return rows with server_updated_at >= since (ISO-8601)",
    ),
    include_deleted: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
) -> SyncPullResponse:
    w_stmt = (
        select(WorkoutLog)
        .options(selectinload(WorkoutLog.exercise_items))
        .where(WorkoutLog.user_id == user.id)
    )
    d_stmt = (
        select(DietLog)
        .options(selectinload(DietLog.macro_items))
        .where(DietLog.user_id == user.id)
    )
    if not include_deleted:
        w_stmt = w_stmt.where(WorkoutLog.is_deleted.is_(False))
        d_stmt = d_stmt.where(DietLog.is_deleted.is_(False))
    if since is not None:
        w_stmt = w_stmt.where(WorkoutLog.server_updated_at >= since)
        d_stmt = d_stmt.where(DietLog.server_updated_at >= since)
    w_stmt = w_stmt.order_by(WorkoutLog.server_updated_at.asc()).limit(limit)
    d_stmt = d_stmt.order_by(DietLog.server_updated_at.asc()).limit(limit)

    wr = await db.execute(w_stmt)
    dr = await db.execute(d_stmt)
    workouts = list(wr.scalars().all())
    diets = list(dr.scalars().all())

    since_str = since.isoformat() if since else None

    return SyncPullResponse(
        since=since_str,
        workouts=[WorkoutRead.model_validate(w) for w in workouts],
        diets=[DietRead.model_validate(d) for d in diets],
    )
