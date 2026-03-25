from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.core.time import UTC
from app.db.base import Base
import app.db.session as db_session_module
from app.db.session import get_db
from app.main import app, fastapi_app
from app.models import DietMacroItem, RequestAudit, WorkoutExerciseItem  # noqa: F401
from app.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    e = create_async_engine(TEST_DATABASE_URL)
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    prev_session_local = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = factory

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        db_session_module.AsyncSessionLocal = prev_session_local
        fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(engine) -> dict[str, str]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        u = User(
            apple_user_id="test-apple-sub",
            email="test@example.com",
            created_at=datetime.now(UTC),
            last_sync_at=None,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        token = create_access_token(subject=u.id)
    return {"Authorization": f"Bearer {token}"}
