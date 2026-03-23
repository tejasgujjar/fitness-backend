from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import LogSource


class WorkoutCreate(BaseModel):
    local_id: UUID
    created_at_local: datetime | None = None
    updated_at_local: datetime | None = None
    raw_input: str | None = None
    source: LogSource | None = None
    transcript_confidence: float | None = None
    transcript_locale: str | None = None
    workout_type: str | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    intensity: str | None = None
    notes: str | None = None
    calories_estimate: float | None = None


class WorkoutPatch(BaseModel):
    created_at_local: datetime | None = None
    updated_at_local: datetime | None = None
    is_deleted: bool | None = None
    raw_input: str | None = None
    source: LogSource | None = None
    transcript_confidence: float | None = None
    transcript_locale: str | None = None
    workout_type: str | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    intensity: str | None = None
    notes: str | None = None
    calories_estimate: float | None = None


class WorkoutExerciseItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    sort_order: int
    name: str
    sets: int
    reps: int
    weight_lb: float
    workout_type: str
    rpe: float | None
    time_minutes: float | None
    assumption: str
    sport_name: str
    calories_burn: float


class WorkoutRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    local_id: UUID
    created_at_local: datetime | None
    updated_at_local: datetime | None
    server_updated_at: datetime
    is_deleted: bool
    raw_input: str | None
    source: LogSource | None
    transcript_confidence: float | None
    transcript_locale: str | None
    workout_type: str | None
    duration_minutes: int | None
    distance_km: float | None
    intensity: str | None
    notes: str | None
    calories_estimate: float | None
    exercise_items: list[WorkoutExerciseItemRead] = []
