from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_create_and_list_workout(client, auth_headers):
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

    r2 = await client.get("/workouts", headers=auth_headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["id"] == data["id"]
