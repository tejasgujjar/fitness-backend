from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.diet import DietRead
from app.schemas.workout import WorkoutRead


class SyncItemIn(BaseModel):
    entity_type: Literal["workout", "diet"]
    local_id: UUID
    operation: Literal["create", "update", "delete"]
    payload: dict[str, Any] | None = None


class SyncPushRequest(BaseModel):
    items: list[SyncItemIn] = Field(default_factory=list)


class SyncItemResult(BaseModel):
    local_id: UUID
    ok: bool
    error: str | None = None


class SyncPushResponse(BaseModel):
    mappings: dict[str, str] = Field(
        default_factory=dict,
        description="local_id (string) -> server id (string) for successful creates",
    )
    results: list[SyncItemResult]


class SyncPullResponse(BaseModel):
    since: str | None = None
    workouts: list[WorkoutRead]
    diets: list[DietRead]
