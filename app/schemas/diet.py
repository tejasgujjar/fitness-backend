from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from app.models.enums import LogSource
from app.schemas.agent_outputs import DietMacroItemParsed


class DietCreate(BaseModel):
    local_id: UUID
    created_at_local: datetime | None = None
    updated_at_local: datetime | None = None
    raw_input: str | None = None
    source: LogSource | None = None
    transcript_confidence: float | None = None
    transcript_locale: str | None = None
    meal_type: str | None = None
    items_text: str | None = None
    notes: str | None = None
    calories_estimate: float | None = None
    protein_grams: float | None = None
    carbs_grams: float | None = None
    fat_grams: float | None = None
    macro_items: list[DietMacroItemParsed] = Field(
        default_factory=list,
        validation_alias=AliasChoices("macro_items", "macros"),
    )


class DietPatch(BaseModel):
    created_at_local: datetime | None = None
    updated_at_local: datetime | None = None
    is_deleted: bool | None = None
    raw_input: str | None = None
    source: LogSource | None = None
    transcript_confidence: float | None = None
    transcript_locale: str | None = None
    meal_type: str | None = None
    items_text: str | None = None
    notes: str | None = None
    calories_estimate: float | None = None
    protein_grams: float | None = None
    carbs_grams: float | None = None
    fat_grams: float | None = None


class DietMacroItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    sort_order: int
    food: str
    qty: float
    weight: float
    unit: str
    carbs: float
    cals: float
    protein: float
    fats: float
    fiber: float
    assumptions: str


class DietRead(BaseModel):
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
    meal_type: str | None
    items_text: str | None
    notes: str | None
    calories_estimate: float | None
    protein_grams: float | None
    carbs_grams: float | None
    fat_grams: float | None
    macro_items: list[DietMacroItemRead] = []
