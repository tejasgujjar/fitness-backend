from __future__ import annotations

import uuid

import pytest

from app.schemas.agent_outputs import DietMacroItemParsed, DietParsedOutput
from app.services.agent_parser import AgentInvocationError


@pytest.mark.asyncio
async def test_create_diet_raw_input_optional(client, auth_headers):
    lid = str(uuid.uuid4())
    r = await client.post(
        "/diet",
        json={"local_id": lid, "meal_type": "breakfast", "calories_estimate": 420},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert data["meal_type"] == "breakfast"
    assert data["calories_estimate"] == 420
    assert data["raw_input"] is None
    assert data["macro_items"] == []


@pytest.mark.asyncio
async def test_diet_breakdown_success(client, auth_headers, monkeypatch):
    async def fake_food_agent(raw_input: str) -> DietParsedOutput:
        assert raw_input == "40g oats"
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

    monkeypatch.setattr("app.api.routes.diet.call_food_agent", fake_food_agent)
    r = await client.get(
        "/diet/breakdown",
        params={"raw_input": "40g oats"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["macros"]) == 1
    assert data["macros"][0]["food"] == "Oats"


@pytest.mark.asyncio
async def test_diet_breakdown_requires_non_empty_raw_input(client, auth_headers):
    r = await client.get(
        "/diet/breakdown",
        params={"raw_input": "   "},
        headers=auth_headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_diet_breakdown_agent_error_returns_502(client, auth_headers, monkeypatch):
    async def boom(_: str) -> DietParsedOutput:
        raise AgentInvocationError("simulated failure")

    monkeypatch.setattr("app.api.routes.diet.call_food_agent", boom)
    r = await client.get(
        "/diet/breakdown",
        params={"raw_input": "40g oats"},
        headers=auth_headers,
    )
    assert r.status_code == 502


@pytest.mark.asyncio
async def test_create_and_list_diet_persists_payload_only(client, auth_headers, monkeypatch):
    async def boom(_: str) -> DietParsedOutput:
        raise AssertionError("POST /diet should not call agent")

    monkeypatch.setattr("app.api.routes.diet.call_food_agent", boom)
    lid = str(uuid.uuid4())
    body = {
        "local_id": lid,
        "raw_input": "40g oats",
        "source": "text",
        "calories_estimate": 156,
    }
    r = await client.post("/diet", json=body, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert data["calories_estimate"] == 156
    assert data["macro_items"] == []

    r2 = await client.get("/diet", headers=auth_headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["id"] == data["id"]
    assert rows[0]["macro_items"] == []


@pytest.mark.asyncio
async def test_create_diet_persists_macro_items_from_payload(client, auth_headers):
    lid = str(uuid.uuid4())
    body = {
        "local_id": lid,
        "meal_type": "breakfast",
        "macros": [
            {
                "food": "Oats",
                "qty": 1,
                "weight": 40,
                "unit": "g",
                "carbs": 25,
                "cals": 156,
                "protein": 5,
                "fats": 3,
                "fiber": 4,
                "assumptions": "Rolled oats",
            },
        ],
    }
    r = await client.post("/diet", json=body, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["local_id"] == lid
    assert len(data["macro_items"]) == 1
    assert data["macro_items"][0]["food"] == "Oats"
    assert data["macro_items"][0]["carbs"] == 25

    r2 = await client.get("/diet", headers=auth_headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert len(rows[0]["macro_items"]) == 1
    assert rows[0]["macro_items"][0]["food"] == "Oats"


@pytest.mark.asyncio
async def test_create_diet_idempotent_attaches_macros_when_log_had_none(
    client,
    auth_headers,
):
    """If diet_logs row exists for local_id without children, a retry with macros fills diet_macro_items."""
    lid = str(uuid.uuid4())
    r1 = await client.post(
        "/diet",
        json={"local_id": lid, "raw_input": "2 banana"},
        headers=auth_headers,
    )
    assert r1.status_code == 201
    assert r1.json()["macro_items"] == []

    r2 = await client.post(
        "/diet",
        json={
            "local_id": lid,
            "raw_input": "2 banana",
            "macros": [
                {
                    "food": "Banana",
                    "qty": 2,
                    "weight": 240,
                    "unit": "grams",
                    "carbs": 54,
                    "cals": 210,
                    "protein": 2.4,
                    "fats": 0.6,
                    "fiber": 6,
                    "assumptions": "test",
                },
            ],
        },
        headers=auth_headers,
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]
    assert len(r2.json()["macro_items"]) == 1
    assert r2.json()["macro_items"][0]["food"] == "Banana"


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

    monkeypatch.setattr("app.api.routes.diet.call_food_agent", fake_food_agent)

    lid = str(uuid.uuid4())
    body = {"local_id": lid, "raw_input": "test"}
    r1 = await client.post("/diet", json=body, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/diet", json=body, headers=auth_headers)
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]
    assert calls["n"] == 0
