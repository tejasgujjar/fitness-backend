from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.account_deletion_history import AccountDeletionHistory
from app.models.diet_log import DietLog
from app.models.request_audit import RequestAudit
from app.models.user import User
from app.models.workout_log import WorkoutLog


@pytest.mark.asyncio
async def test_delete_me_requires_auth(client):
    r = await client.request("DELETE", "/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_me_deletes_user_data_and_writes_snapshot(client, engine, auth_headers):
    workout_local_id = str(uuid4())
    diet_local_id = str(uuid4())

    workout_response = await client.post(
        "/workouts",
        json={"local_id": workout_local_id, "workout_type": "run"},
        headers=auth_headers,
    )
    assert workout_response.status_code == 201

    diet_response = await client.post(
        "/diet",
        json={"local_id": diet_local_id, "meal_type": "lunch"},
        headers=auth_headers,
    )
    assert diet_response.status_code == 201

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    request_audit_id = uuid4()
    user_id = None
    async with factory() as session:
        user_id = (await session.execute(select(User.id))).scalar_one()
        session.add(
            RequestAudit(
                request_id=request_audit_id,
                method="DELETE",
                path="/debug/request-audit",
                user_id=user_id,
            ),
        )
        await session.commit()

    delete_response = await client.request(
        "DELETE",
        "/me",
        json={
            "trigger": "self_service",
            "appVersion": "1.0.0",
            "deviceId": "ios-device-123",
        },
        headers={**auth_headers, "User-Agent": "pytest-delete-client"},
    )
    assert delete_response.status_code == 204

    me_response = await client.get("/me", headers=auth_headers)
    assert me_response.status_code == 401

    async with factory() as session:
        remaining_user = (await session.execute(select(User))).scalar_one_or_none()
        assert remaining_user is None

        workout_count = await session.scalar(select(func.count()).select_from(WorkoutLog))
        diet_count = await session.scalar(select(func.count()).select_from(DietLog))
        assert workout_count == 0
        assert diet_count == 0

        history_row = (await session.execute(select(AccountDeletionHistory))).scalar_one()
        assert history_row.user_id == user_id
        assert history_row.email == "test@example.com"
        assert history_row.apple_user_id == "test-apple-sub"
        assert history_row.trigger == "self_service"
        assert history_row.workout_logs_deleted_count == 1
        assert history_row.diet_logs_deleted_count == 1
        assert history_row.app_version == "1.0.0"
        assert history_row.device_id == "ios-device-123"
        assert history_row.user_agent == "pytest-delete-client"

        request_audit_row = (
            await session.execute(
                select(RequestAudit).where(RequestAudit.request_id == request_audit_id),
            )
        ).scalar_one_or_none()
        assert request_audit_row is not None
