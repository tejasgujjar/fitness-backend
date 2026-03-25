from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import UTC
from app.db.session import get_db
from app.deps import get_current_user
from app.models.diet_log import DietLog
from app.models.user import User
from app.schemas.agent_outputs import DietParsedOutput
from app.schemas.diet import DietCreate, DietPatch, DietRead
from app.schemas.sync import SyncItemIn
from app.services.agent_parser import AgentInvocationError, call_food_agent
from app.services.sync import (
    attach_macros_if_missing,
    get_diet_by_local,
    now_utc,
    upsert_diet_from_create,
)

router = APIRouter()


@router.post("", response_model=DietRead, status_code=status.HTTP_201_CREATED)
async def create_diet(
    body: DietCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> DietLog:
    now = now_utc()
    existing = await get_diet_by_local(db, user.id, body.local_id)
    if existing:
        await attach_macros_if_missing(db, existing, body.macro_items)
        result = await db.execute(
            select(DietLog)
            .options(selectinload(DietLog.macro_items))
            .where(DietLog.id == existing.id),
        )
        return result.scalar_one()

    item = SyncItemIn(
        entity_type="diet",
        local_id=body.local_id,
        operation="create",
        payload=body.model_dump(mode="json"),
    )
    row = await upsert_diet_from_create(
        db,
        user,
        item,
        now,
        macro_items=body.macro_items or None,
    )
    result = await db.execute(
        select(DietLog)
        .options(selectinload(DietLog.macro_items))
        .where(DietLog.id == row.id),
    )
    return result.scalar_one()


@router.get("/breakdown", response_model=DietParsedOutput)
async def diet_breakdown(
    raw_input: str = Query(..., description="Raw diet input to parse"),
) -> DietParsedOutput:
    if not raw_input.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="raw_input is required for diet breakdown",
        )
    try:
        return await call_food_agent(raw_input)
    except AgentInvocationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e


@router.get("", response_model=list[DietRead])
async def list_diet_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    since: datetime | None = Query(
        None,
        description="Return rows with server_updated_at >= since (ISO-8601)",
    ),
    include_deleted: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[DietLog]:
    stmt = (
        select(DietLog)
        .options(selectinload(DietLog.macro_items))
        .where(DietLog.user_id == user.id)
    )
    if not include_deleted:
        stmt = stmt.where(DietLog.is_deleted.is_(False))
    if since is not None:
        stmt = stmt.where(DietLog.server_updated_at >= since)
    stmt = (
        stmt.order_by(DietLog.server_updated_at.asc(), DietLog.id.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{diet_id}", response_model=DietRead)
async def get_diet_log(
    diet_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> DietLog:
    result = await db.execute(
        select(DietLog)
        .options(selectinload(DietLog.macro_items))
        .where(
            DietLog.id == diet_id,
            DietLog.user_id == user.id,
        ),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.patch("/{diet_id}", response_model=DietRead)
async def patch_diet_log(
    diet_id: UUID,
    body: DietPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> DietLog:
    result = await db.execute(
        select(DietLog)
        .options(selectinload(DietLog.macro_items))
        .where(
            DietLog.id == diet_id,
            DietLog.user_id == user.id,
        ),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.server_updated_at = datetime.now(UTC)
    return row


@router.delete("/{diet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diet_log(
    diet_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    result = await db.execute(
        sql_delete(DietLog).where(
            DietLog.id == diet_id,
            DietLog.user_id == user.id,
        ),
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
