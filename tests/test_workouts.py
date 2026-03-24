from __future__ import annotations

import uuid

import pytest

from app.schemas.agent_outputs import WorkoutExerciseParsed, WorkoutParsedOutput
from app.services.agent_parser import AgentInvocationError


@pytest.mark.asyncio
async def test_create_workout_raw_input_optional(client, auth_headers):
    lid = str(uuid.uuid4())
    r = await client.post(
        "/workouts",
        json={"local_id": lid, "workout_type": "run", "duration_minutes": 20},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert data["workout_type"] == "run"
    assert data["duration_minutes"] == 20
    assert data["raw_input"] is None
    assert data["exercise_items"] == []


@pytest.mark.asyncio
async def test_workout_breakdown_agent_error_returns_502(
    client,
    auth_headers,
    monkeypatch,
):
    async def boom(_: str) -> WorkoutParsedOutput:
        raise AgentInvocationError("simulated failure")

    monkeypatch.setattr("app.api.routes.workouts.call_workout_agent", boom)
    r = await client.get(
        "/workouts/breakdown",
        params={"raw_input": "run"},
        headers=auth_headers,
    )
    assert r.status_code == 502


@pytest.mark.asyncio
async def test_workout_breakdown_requires_non_empty_raw_input(client, auth_headers):
    r = await client.get(
        "/workouts/breakdown",
        params={"raw_input": "   "},
        headers=auth_headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_workout_breakdown_success(client, auth_headers, monkeypatch):
    async def fake_workout_agent(raw_input: str) -> WorkoutParsedOutput:
        assert raw_input == "ran 5k"
        return WorkoutParsedOutput(
            analysis="Good run.",
            exercises=[
                WorkoutExerciseParsed(
                    name="5k Run",
                    sets=1,
                    reps=1,
                    weight_lb=0,
                    workout_type="run",
                    rpe=7,
                    time_minutes=30,
                    assumption="pace",
                    sport_name="Running",
                    calories_burn=300,
                ),
            ],
        )

    monkeypatch.setattr("app.api.routes.workouts.call_workout_agent", fake_workout_agent)
    r = await client.get(
        "/workouts/breakdown",
        params={"raw_input": "ran 5k"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["analysis"] == "Good run."
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "5k Run"


@pytest.mark.asyncio
async def test_create_and_list_workout_persists_llm_payload(
    client,
    auth_headers,
    monkeypatch,
):
    async def boom(_: str) -> WorkoutParsedOutput:
        raise AssertionError("POST /workouts should not call agent")

    monkeypatch.setattr("app.api.routes.workouts.call_workout_agent", boom)
    lid = str(uuid.uuid4())
    body = {
        "local_id": lid,
        "analysis": "Steady run workout.",
        "exercises": [
            {
                "name": "5k Run",
                "sets": 1,
                "reps": 1,
                "weight_lb": 0,
                "workout_type": "sports",
                "rpe": 7,
                "time_minutes": 30,
                "assumption": "Average pace assumed from text.",
                "sport_name": "Running",
                "calories_burn": 300,
            },
        ],
    }
    r = await client.post("/workouts", json=body, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert data["workout_type"] == "sports"
    assert data["duration_minutes"] == 30
    assert data["calories_estimate"] == 300
    assert data["notes"] == "Steady run workout."
    assert data["llm_payload"] == {
        "analysis": "Steady run workout.",
        "exercises": [
            {
                "name": "5k Run",
                "sets": 1,
                "reps": 1,
                "weight_lb": 0.0,
                "workout_type": "sports",
                "rpe": 7.0,
                "time_minutes": 30.0,
                "assumption": "Average pace assumed from text.",
                "sport_name": "Running",
                "calories_burn": 300.0,
            },
        ],
    }
    assert len(data["exercise_items"]) == 1
    assert data["exercise_items"][0]["assumption"] == "Average pace assumed from text."
    assert data["exercise_items"][0]["sport_name"] == "Running"
    assert data["exercise_items"][0]["calories_burn"] == 300

    r2 = await client.get("/workouts", headers=auth_headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["id"] == data["id"]
    assert rows[0]["llm_payload"] == data["llm_payload"]
    assert rows[0]["exercise_items"][0]["assumption"] == "Average pace assumed from text."


@pytest.mark.asyncio
async def test_workout_idempotent_same_local_id_reuses_existing_row(client, auth_headers):
    lid = str(uuid.uuid4())
    body = {
        "local_id": lid,
        "analysis": "Workout summary.",
        "exercises": [
            {
                "name": "Squat",
                "sets": 3,
                "reps": 5,
                "weight_lb": 185,
                "workout_type": "legs",
                "rpe": 8,
                "time_minutes": 20,
                "assumption": "Weight inferred from previous logs.",
                "sport_name": "",
                "calories_burn": 180,
            },
        ],
    }
    r1 = await client.post("/workouts", json=body, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/workouts", json=body, headers=auth_headers)
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    r3 = await client.get("/workouts", headers=auth_headers)
    assert r3.status_code == 200
    rows = r3.json()
    assert len(rows) == 1
    assert len(rows[0]["exercise_items"]) == 1
