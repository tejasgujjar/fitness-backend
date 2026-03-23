from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.diet_log import DietLog


class DietMacroItem(Base):
    __tablename__ = "diet_macro_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    diet_log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("diet_logs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    food: Mapped[str] = mapped_column(String(512), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    cals: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    fats: Mapped[float] = mapped_column(Float, nullable=False)
    fiber: Mapped[float] = mapped_column(Float, nullable=False)
    assumptions: Mapped[str] = mapped_column(Text, nullable=False, default="")

    diet_log: Mapped["DietLog"] = relationship(back_populates="macro_items")
