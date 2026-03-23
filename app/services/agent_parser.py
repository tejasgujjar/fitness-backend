from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, TypeVar

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.agent_outputs import DietParsedOutput, WorkoutParsedOutput

log = logging.getLogger(__name__)

workout_prompt = """
You are a helpful workout agent. Analyze the workout log and return a structured response.

Output requirements:
- Return valid JSON only.
- The root object must contain exactly two fields: "analysis" and "exercises".
- "analysis" is a concise textual summary of the full workout.
- "exercises" is an array of exercise objects.
- Each exercise object must contain all required fields:
  name, sets, reps, weight_lb, workout_type, rpe, time_minutes, assumption, sport_name, calories_burn.
- workout_type must be one of: push, pull, legs, core, sports, general.
- Use numeric values for sets/reps/weight_lb/rpe/time_minutes/calories_burn.
- If a value is unknown, infer a reasonable value and explain that inference in "assumption".
- If weight is not applicable, set weight_lb to 0.
- If not a sport, set sport_name to "".
- Do not include markdown, comments, or extra keys.

Expected JSON shape:
{
  "analysis": "Textual analysis or summary of the entire workout",
  "exercises": [
    {
      "name": "Exercise name",
      "sets": 0,
      "reps": 0,
      "weight_lb": 0,
      "workout_type": "general",
      "rpe": 0,
      "time_minutes": 0,
      "assumption": "",
      "sport_name": "",
      "calories_burn": 0
    }
  ]
}
"""
food_prompt = """
You are a diet agent. Analyze the food log and return a structured macro breakdown.

Output requirements:
- Return valid JSON only.
- The root object must contain exactly one field: "macros".
- "macros" must be an array of food macro objects.
- Each macro object must contain all required fields:
  food, qty, weight, unit, carbs, cals, protein, fats, fiber, assumptions.
- Use numeric values for qty/weight/carbs/cals/protein/fats/fiber.
- If details are missing, infer reasonable values and document assumptions.
- Do not include markdown, comments, or extra keys.

Expected JSON shape:
{
  "macros": [
    {
      "food": "",
      "qty": 0,
      "weight": 0,
      "unit": "",
      "carbs": 0,
      "cals": 0,
      "protein": 0,
      "fats": 0,
      "fiber": 0,
      "assumptions": ""
    }
  ]
}
"""
FOOD_PREFIX = f"{food_prompt}\nFOOD LOG: "
WORKOUT_PREFIX = f"{workout_prompt}\nWORKOUT LOG: "

TOut = TypeVar("TOut", DietParsedOutput, WorkoutParsedOutput)


class AgentInvocationError(Exception):
    """Raised when the OpenAI agent response cannot be parsed."""


@lru_cache
def _get_async_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        msg = "OPENAI_API_KEY is not configured"
        raise AgentInvocationError(msg)
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
    )


def _responses_extra_body() -> dict[str, Any]:
    """Merge Agent Builder id if provided (API may evolve; extra_body is forward-compatible)."""
    settings = get_settings()
    extra: dict[str, Any] = {}
    if settings.OPENAI_AGENT_ID:
        extra["agent"] = settings.OPENAI_AGENT_ID
    return extra


def _parse_from_response(resp: Any, model: type[TOut]) -> TOut:
    parsed = getattr(resp, "output_parsed", None)
    if parsed is not None:
        if isinstance(parsed, model):
            return parsed
        if isinstance(parsed, dict):
            return model.model_validate(parsed)

    text = getattr(resp, "output_text", "") or ""
    text = text.strip()
    if not text:
        msg = "Empty agent output"
        raise AgentInvocationError(msg)
    try:
        return model.model_validate_json(text)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        data = json.loads(text)
        return model.model_validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("Failed to parse agent output: %s", text[:500])
        msg = f"Invalid agent JSON output: {e}"
        raise AgentInvocationError(msg) from e


async def call_food_agent(raw_input: str) -> DietParsedOutput:
    text = raw_input.strip()
    if not text:
        msg = "raw_input is empty"
        raise AgentInvocationError(msg)
    settings = get_settings()
    client = _get_async_client()
    prefixed = f"{FOOD_PREFIX}{text}"
    extra = _responses_extra_body()
    try:
        resp = await client.responses.parse(
            model=settings.OPENAI_MODEL,
            input=prefixed,
            text_format=DietParsedOutput,
            extra_body=extra or None,
        )
    except Exception as e:
        log.exception("OpenAI diet agent call failed")
        msg = f"OpenAI request failed: {e}"
        raise AgentInvocationError(msg) from e
    return _parse_from_response(resp, DietParsedOutput)


async def call_workout_agent(raw_input: str) -> WorkoutParsedOutput:
    text = raw_input.strip()
    if not text:
        msg = "raw_input is empty"
        raise AgentInvocationError(msg)
    settings = get_settings()
    client = _get_async_client()
    prefixed = f"{WORKOUT_PREFIX}{text}"
    extra = _responses_extra_body()
    try:
        resp = await client.responses.parse(
            model=settings.OPENAI_MODEL,
            input=prefixed,
            text_format=WorkoutParsedOutput,
            extra_body=extra or None,
        )
    except Exception as e:
        log.exception("OpenAI workout agent call failed")
        msg = f"OpenAI request failed: {e}"
        raise AgentInvocationError(msg) from e
    return _parse_from_response(resp, WorkoutParsedOutput)
