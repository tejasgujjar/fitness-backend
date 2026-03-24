from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diet_log import DietLog
from app.models.diet_macro_item import DietMacroItem
from app.models.user import User
from app.models.workout_exercise_item import WorkoutExerciseItem
from app.models.workout_log import WorkoutLog
from app.schemas.agent_outputs import (
    DietMacroItemParsed,
    DietParsedOutput,
    WorkoutExerciseParsed,
    WorkoutParsedOutput,
)
from app.schemas.diet import DietCreate, DietPatch
from app.schemas.sync import SyncItemIn, SyncItemResult
from app.schemas.workout import WorkoutCreate, WorkoutPatch
from app.core.time import UTC

def _is_workout_local_unique_violation(exc: IntegrityError) -> bool:
    return "uq_workout_user_local" in str(exc)


def _is_diet_local_unique_violation(exc: IntegrityError) -> bool:
    return "uq_diet_user_local" in str(exc)


async def _attach_exercises_if_missing(
    db: AsyncSession,
    row: WorkoutLog,
    exercise_items: list[WorkoutExerciseParsed] | None,
) -> None:
    if not exercise_items:
        return
    r = await db.execute(
        select(WorkoutExerciseItem.id)
        .where(WorkoutExerciseItem.workout_log_id == row.id)
        .limit(1),
    )
    has_children = r.scalar_one_or_none() is not None
    if has_children:
        return
    for child in _workout_exercise_rows(row.id, exercise_items):
        db.add(child)
    await db.flush()


async def _attach_macros_if_missing(
    db: AsyncSession,
    row: DietLog,
    macro_items: list[DietMacroItemParsed] | None,
) -> None:
    if not macro_items:
        return
    r = await db.execute(
        select(DietMacroItem.id).where(DietMacroItem.diet_log_id == row.id).limit(1),
    )
    has_children = r.scalar_one_or_none() is not None
    if has_children:
        return
    for child in _diet_macro_rows(row.id, macro_items):
        db.add(child)
    await db.flush()


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


async def get_workout_by_local(
    db: AsyncSession,
    user_id: UUID,
    local_id: UUID,
) -> WorkoutLog | None:
    return await _get_workout_by_local(db, user_id, local_id)


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


async def get_diet_by_local(
    db: AsyncSession,
    user_id: UUID,
    local_id: UUID,
) -> DietLog | None:
    """Public wrapper for idempotent diet lookups."""
    return await _get_diet_by_local(db, user_id, local_id)


def enrich_diet_from_parsed(body: DietCreate, parsed: DietParsedOutput) -> DietCreate:
    carbs = sum(m.carbs for m in parsed.macros)
    protein = sum(m.protein for m in parsed.macros)
    fat = sum(m.fats for m in parsed.macros)
    cals = sum(m.cals for m in parsed.macros)
    foods = ", ".join(m.food for m in parsed.macros)
    merged = body.model_dump()
    merged["calories_estimate"] = cals
    merged["protein_grams"] = protein
    merged["carbs_grams"] = carbs
    merged["fat_grams"] = fat
    if foods:
        merged["items_text"] = foods
    return DietCreate.model_validate(merged)


def enrich_workout_from_parsed(body: WorkoutCreate, parsed: WorkoutParsedOutput) -> WorkoutCreate:
    merged = body.model_dump()
    merged["notes"] = parsed.analysis
    merged["calories_estimate"] = sum(e.calories_burn for e in parsed.exercises)
    total_min = sum(float(e.time_minutes or 0) for e in parsed.exercises)
    if total_min > 0:
        merged["duration_minutes"] = int(round(total_min))
    if parsed.exercises:
        merged["workout_type"] = parsed.exercises[0].workout_type
    return WorkoutCreate.model_validate(merged)


def _diet_macro_rows(
    diet_log_id: UUID,
    items: list[DietMacroItemParsed],
) -> list[DietMacroItem]:
    rows: list[DietMacroItem] = []
    for i, m in enumerate(items):
        rows.append(
            DietMacroItem(
                diet_log_id=diet_log_id,
                sort_order=i,
                food=m.food,
                qty=m.qty,
                weight=m.weight,
                unit=m.unit,
                carbs=m.carbs,
                cals=m.cals,
                protein=m.protein,
                fats=m.fats,
                fiber=m.fiber,
                assumptions=m.assumptions,
            ),
        )
    return rows


def _workout_exercise_rows(
    workout_log_id: UUID,
    items: list[WorkoutExerciseParsed],
) -> list[WorkoutExerciseItem]:
    rows: list[WorkoutExerciseItem] = []
    for i, e in enumerate(items):
        rpe_val: float | None
        if e.rpe is None:
            rpe_val = None
        elif isinstance(e.rpe, float):
            rpe_val = e.rpe
        else:
            rpe_val = float(e.rpe)
        tm: float | None
        if e.time_minutes is None:
            tm = None
        elif isinstance(e.time_minutes, float):
            tm = e.time_minutes
        else:
            tm = float(e.time_minutes)
        rows.append(
            WorkoutExerciseItem(
                workout_log_id=workout_log_id,
                sort_order=i,
                name=e.name,
                sets=e.sets,
                reps=e.reps,
                weight_lb=e.weight_lb,
                workout_type=e.workout_type,
                rpe=rpe_val,
                time_minutes=tm,
                assumption=e.assumption,
                sport_name=e.sport_name,
                calories_burn=e.calories_burn,
            ),
        )
    return rows


async def upsert_workout_from_create(
    db: AsyncSession,
    user: User,
    item: SyncItemIn,
    now: datetime,
    *,
    exercise_items: list[WorkoutExerciseParsed] | None = None,
    llm_payload: dict[str, Any] | None = None,
) -> WorkoutLog:
    payload = item.payload or {}
    body = WorkoutCreate.model_validate({**payload, "local_id": item.local_id})
    parsed: WorkoutParsedOutput | None = None
    if body.analysis is not None or body.exercises:
        parsed = WorkoutParsedOutput(
            analysis=body.analysis or "",
            exercises=body.exercises,
        )
        body = enrich_workout_from_parsed(body, parsed)
        if exercise_items is None:
            exercise_items = parsed.exercises
        if llm_payload is None:
            llm_payload = parsed.model_dump(mode="json")
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
        llm_payload=llm_payload,
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
            if exercise_items:
                for child in _workout_exercise_rows(row.id, exercise_items):
                    db.add(child)
                await db.flush()
    except IntegrityError as exc:
        if not _is_workout_local_unique_violation(exc):
            raise
        existing_after_conflict = await _get_workout_by_local(db, user.id, item.local_id)
        if existing_after_conflict is None:
            raise
        await _attach_exercises_if_missing(db, existing_after_conflict, exercise_items)
        return existing_after_conflict
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
    *,
    macro_items: list[DietMacroItemParsed] | None = None,
) -> DietLog:
    payload = item.payload or {}
    body = DietCreate.model_validate({**payload, "local_id": item.local_id})
    effective_macro_items = macro_items if macro_items is not None else body.macro_items
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
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
            if effective_macro_items:
                for child in _diet_macro_rows(row.id, effective_macro_items):
                    db.add(child)
                await db.flush()
    except IntegrityError as exc:
        if not _is_diet_local_unique_violation(exc):
            raise
        existing_after_conflict = await _get_diet_by_local(db, user.id, item.local_id)
        if existing_after_conflict is None:
            raise
        await _attach_macros_if_missing(db, existing_after_conflict, effective_macro_items)
        return existing_after_conflict
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
