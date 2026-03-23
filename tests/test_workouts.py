from __future__ import annotations

import uuid

import pytest

from app.schemas.agent_outputs import WorkoutExerciseParsed, WorkoutParsedOutput
from app.services.agent_parser import AgentInvocationError


@pytest.mark.asyncio
async def test_create_workout_requires_raw_input(client, auth_headers):
    lid = str(uuid.uuid4())
    r = await client.post(
        "/workouts",
        json={"local_id": lid},
        headers=auth_headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_workout_agent_error_returns_502(client, auth_headers, monkeypatch):
    async def boom(_: str):
        raise AgentInvocationError("simulated failure")

    monkeypatch.setattr(
        "app.api.routes.workouts.call_workout_agent",
        boom,
    )
    lid = str(uuid.uuid4())
    r = await client.post(
        "/workouts",
        json={"local_id": lid, "raw_input": "run"},
        headers=auth_headers,
    )
    assert r.status_code == 502


@pytest.mark.asyncio
async def test_create_and_list_workout(client, auth_headers, monkeypatch):
    async def fake_workout_agent(raw_input: str) -> WorkoutParsedOutput:
        assert raw_input.strip()
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

    monkeypatch.setattr(
        "app.api.routes.workouts.call_workout_agent",
        fake_workout_agent,
    )

    lid = str(uuid.uuid4())
    body = {
        "local_id": lid,
        "raw_input": "ran 5k",
        "source": "text",
        "workout_type": "run",
        "duration_minutes": 30,
    }
    r = await client.post("/workouts", json=body, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert data["workout_type"] == "run"
    assert data["notes"] == "Good run."
    assert len(data["exercise_items"]) == 1
    assert data["exercise_items"][0]["name"] == "5k Run"

    r2 = await client.get("/workouts", headers=auth_headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["id"] == data["id"]
