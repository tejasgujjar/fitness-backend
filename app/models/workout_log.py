from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import LogSource

if TYPE_CHECKING:
    from app.models.user import User


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    local_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    created_at_local: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at_local: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    server_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[LogSource]] = mapped_column(
        Enum(LogSource, name="log_source", native_enum=False, length=16),
        nullable=True,
    )
    transcript_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transcript_locale: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    workout_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intensity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calories_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="workout_logs")

    __table_args__ = (
        UniqueConstraint("user_id", "local_id", name="uq_workout_user_local"),
        Index("ix_workout_logs_user_server_updated", "user_id", "server_updated_at"),
    )
