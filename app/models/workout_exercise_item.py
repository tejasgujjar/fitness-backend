from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.workout_log import WorkoutLog


class WorkoutExerciseItem(Base):
    __tablename__ = "workout_exercise_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    workout_log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workout_logs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_lb: Mapped[float] = mapped_column(Float, nullable=False)
    workout_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    assumption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sport_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    calories_burn: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    workout_log: Mapped["WorkoutLog"] = relationship(back_populates="exercise_items")
