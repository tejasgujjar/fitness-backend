from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diet_log import DietLog
from app.models.user import User
from app.models.workout_log import WorkoutLog
from app.schemas.diet import DietCreate, DietPatch
from app.schemas.sync import SyncItemIn, SyncItemResult
from app.schemas.workout import WorkoutCreate, WorkoutPatch
from app.core.time import UTC


async def _get_workout_by_local(
    db: AsyncSession,
    user_id: UUID,
    local_id: UUID,
) -> WorkoutLog | None:
    r = await db.execute(
        select(WorkoutLog).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.local_id == local_id,
        ),
    )
    return r.scalar_one_or_none()


async def _get_diet_by_local(
    db: AsyncSession,
    user_id: UUID,
    local_id: UUID,
) -> DietLog | None:
    r = await db.execute(
        select(DietLog).where(
            DietLog.user_id == user_id,
            DietLog.local_id == local_id,
        ),
    )
    return r.scalar_one_or_none()


async def upsert_workout_from_create(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> WorkoutLog:
    payload = item.payload or {}
    body = WorkoutCreate.model_validate({**payload, "local_id": item.local_id})
    existing = await _get_workout_by_local(db, user.id, item.local_id)
    if existing:
        return existing

    row = WorkoutLog(
        user_id=user.id,
        local_id=body.local_id,
        created_at_local=body.created_at_local,
        updated_at_local=body.updated_at_local,
        server_updated_at=now,
        is_deleted=False,
        raw_input=body.raw_input,
        source=body.source,
        transcript_confidence=body.transcript_confidence,
        transcript_locale=body.transcript_locale,
        workout_type=body.workout_type,
        duration_minutes=body.duration_minutes,
        distance_km=body.distance_km,
        intensity=body.intensity,
        notes=body.notes,
        calories_estimate=body.calories_estimate,
    )
    db.add(row)
    await db.flush()
    return row


async def update_workout_by_local(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> None:
    payload = item.payload or {}
    patch = WorkoutPatch.model_validate(payload)
    row = await _get_workout_by_local(db, user.id, item.local_id)
    if row is None:
        msg = "Workout not found for local_id"
        raise ValueError(msg)
    data = patch.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.server_updated_at = now


async def soft_delete_workout_by_local(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> None:
    row = await _get_workout_by_local(db, user.id, item.local_id)
    if row is None:
        return
    row.is_deleted = True
    row.server_updated_at = now


async def upsert_diet_from_create(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> DietLog:
    payload = item.payload or {}
    body = DietCreate.model_validate({**payload, "local_id": item.local_id})
    existing = await _get_diet_by_local(db, user.id, item.local_id)
    if existing:
        return existing

    row = DietLog(
        user_id=user.id,
        local_id=body.local_id,
        created_at_local=body.created_at_local,
        updated_at_local=body.updated_at_local,
        server_updated_at=now,
        is_deleted=False,
        raw_input=body.raw_input,
        source=body.source,
        transcript_confidence=body.transcript_confidence,
        transcript_locale=body.transcript_locale,
        meal_type=body.meal_type,
        items_text=body.items_text,
        notes=body.notes,
        calories_estimate=body.calories_estimate,
        protein_grams=body.protein_grams,
        carbs_grams=body.carbs_grams,
        fat_grams=body.fat_grams,
    )
    db.add(row)
    await db.flush()
    return row


async def update_diet_by_local(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> None:
    payload = item.payload or {}
    patch = DietPatch.model_validate(payload)
    row = await _get_diet_by_local(db, user.id, item.local_id)
    if row is None:
        msg = "Diet log not found for local_id"
        raise ValueError(msg)
    data = patch.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.server_updated_at = now


async def soft_delete_diet_by_local(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> None:
    row = await _get_diet_by_local(db, user.id, item.local_id)
    if row is None:
        return
    row.is_deleted = True
    row.server_updated_at = now


async def process_sync_item(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
) -> tuple[SyncItemResult, UUID | None]:
    """
    Returns (result, server_id_for_mapping_if_create_ok).
    server_id is returned for create operations (including idempotent creates).
    """
    try:
        if item.entity_type == "workout":
            if item.operation == "create":
                row = await upsert_workout_from_create(db, user, item, now)
                return (
                    SyncItemResult(local_id=item.local_id, ok=True, error=None),
                    row.id,
                )
            if item.operation == "update":
                await update_workout_by_local(db, user, item, now)
                return SyncItemResult(local_id=item.local_id, ok=True, error=None), None
            if item.operation == "delete":
                await soft_delete_workout_by_local(db, user, item, now)
                return SyncItemResult(local_id=item.local_id, ok=True, error=None), None
            msg = "Unsupported workout operation"
            raise ValueError(msg)
        if item.entity_type == "diet":
            if item.operation == "create":
                row = await upsert_diet_from_create(db, user, item, now)
                return (
                    SyncItemResult(local_id=item.local_id, ok=True, error=None),
                    row.id,
                )
            if item.operation == "update":
                await update_diet_by_local(db, user, item, now)
                return SyncItemResult(local_id=item.local_id, ok=True, error=None), None
            if item.operation == "delete":
                await soft_delete_diet_by_local(db, user, item, now)
                return SyncItemResult(local_id=item.local_id, ok=True, error=None), None
            msg = "Unsupported diet operation"
            raise ValueError(msg)
        msg = "Unsupported entity type"
        raise ValueError(msg)
    except Exception as e:
        return (
            SyncItemResult(local_id=item.local_id, ok=False, error=str(e)),
            None,
        )


def now_utc() -> datetime:
    return datetime.now(UTC)
