from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: process is up (does not require database)."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Readiness: can connect to Postgres (use after DB is configured)."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
