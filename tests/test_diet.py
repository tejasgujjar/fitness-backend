from __future__ import annotations

import uuid

import pytest

from app.schemas.agent_outputs import DietMacroItemParsed, DietParsedOutput


@pytest.mark.asyncio
async def test_create_diet_requires_raw_input(client, auth_headers):
    lid = str(uuid.uuid4())
    r = await client.post(
        "/diet",
        json={"local_id": lid},
        headers=auth_headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_and_list_diet_with_mocked_agent(client, auth_headers, monkeypatch):
    async def fake_food_agent(raw_input: str) -> DietParsedOutput:
        assert raw_input.strip()
        return DietParsedOutput(
            macros=[
                DietMacroItemParsed(
                    food="Oats",
                    qty=1,
                    weight=40,
                    unit="g",
                    carbs=25,
                    cals=156,
                    protein=5,
                    fats=3,
                    fiber=3.5,
                    assumptions="Plain rolled oats.",
                ),
            ],
        )

    monkeypatch.setattr(
        "app.api.routes.diet.call_food_agent",
        fake_food_agent,
    )

    lid = str(uuid.uuid4())
    body = {
        "local_id": lid,
        "raw_input": "40g oats",
        "source": "text",
    }
    r = await client.post("/diet", json=body, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert data["calories_estimate"] == 156
    assert len(data["macro_items"]) == 1
    assert data["macro_items"][0]["food"] == "Oats"

    r2 = await client.get("/diet", headers=auth_headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["id"] == data["id"]
    assert len(rows[0]["macro_items"]) == 1


@pytest.mark.asyncio
async def test_diet_idempotent_same_local_id_no_second_agent_call(
    client,
    auth_headers,
    monkeypatch,
):
    calls = {"n": 0}

    async def fake_food_agent(raw_input: str) -> DietParsedOutput:
        calls["n"] += 1
        return DietParsedOutput(
            macros=[
                DietMacroItemParsed(
                    food="X",
                    qty=1,
                    weight=1,
                    unit="g",
                    carbs=1,
                    cals=1,
                    protein=1,
                    fats=1,
                    fiber=1,
                    assumptions="",
                ),
            ],
        )

    monkeypatch.setattr(
        "app.api.routes.diet.call_food_agent",
        fake_food_agent,
    )

    lid = str(uuid.uuid4())
    body = {"local_id": lid, "raw_input": "test"}
    r1 = await client.post("/diet", json=body, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/diet", json=body, headers=auth_headers)
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]
    assert calls["n"] == 1
