from __future__ import annotations

import logging
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import request_id_var, setup_logging
from app.models.request_audit import RequestAudit


@pytest.mark.asyncio
async def test_health_returns_x_request_id_no_audit_row(client, engine):
    r = await client.get("/health")
    assert r.status_code == 200
    rid_hdr = r.headers.get("x-request-id")
    assert rid_hdr
    UUID(rid_hdr)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        row = (
            await session.execute(select(RequestAudit).where(RequestAudit.request_id == UUID(rid_hdr)))
        ).scalar_one_or_none()
    assert row is None


@pytest.mark.asyncio
async def test_audited_route_persists_request_audit(client, engine):
    r = await client.get("/workouts")
    assert r.status_code == 401
    rid = r.headers.get("x-request-id")
    assert rid

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        row = (
            await session.execute(select(RequestAudit).where(RequestAudit.request_id == UUID(rid)))
        ).scalar_one_or_none()
    assert row is not None
    assert row.status_code == 401
    assert row.method == "GET"
    assert row.path == "/workouts"
    assert row.request_headers is not None
    assert row.response_body is not None


@pytest.mark.asyncio
async def test_client_supplied_request_id_echoed(client, engine):
    custom = str(uuid4())
    r = await client.get("/workouts", headers={"X-Request-ID": custom})
    assert r.headers.get("x-request-id") == custom

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        row = (
            await session.execute(select(RequestAudit).where(RequestAudit.request_id == UUID(custom)))
        ).scalar_one_or_none()
    assert row is not None


def test_log_record_includes_request_id_from_context(caplog):
    setup_logging()
    token = request_id_var.set("550e8400-e29b-41d4-a716-446655440000")
    try:
        with caplog.at_level(logging.INFO):
            logging.getLogger("audit_test_logger").info("probe")
    finally:
        request_id_var.reset(token)
    assert "550e8400-e29b-41d4-a716-446655440000" in caplog.text
