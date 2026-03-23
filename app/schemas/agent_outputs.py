from __future__ import annotations

from pydantic import BaseModel, Field


class DietMacroItemParsed(BaseModel):
    food: str
    qty: float = Field(default=1.0)
    weight: float
    unit: str
    carbs: float
    cals: float
    protein: float
    fats: float
    fiber: float
    assumptions: str = ""


class DietParsedOutput(BaseModel):
    macros: list[DietMacroItemParsed]


class WorkoutExerciseParsed(BaseModel):
    name: str
    sets: int = 1
    reps: int = 1
    weight_lb: float = 0.0
    workout_type: str = "general"
    rpe: float | int | None = None
    time_minutes: float | int | None = None
    assumption: str = ""
    sport_name: str = ""
    calories_burn: float = 0.0


class WorkoutParsedOutput(BaseModel):
    analysis: str
    exercises: list[WorkoutExerciseParsed]
