from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountDeletionHistory(Base):
    __tablename__ = "account_deletion_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    apple_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    trigger: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default="self_service",
    )
    workout_logs_deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diet_logs_deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    app_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
