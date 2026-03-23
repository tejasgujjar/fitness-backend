"""diet macro and workout exercise child tables

Revision ID: 002_macro_exercise
Revises: 001_initial
Create Date: 2026-03-22

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_macro_exercise"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diet_macro_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("diet_log_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("food", sa.String(length=512), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
        sa.Column("cals", sa.Float(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("fats", sa.Float(), nullable=False),
        sa.Column("fiber", sa.Float(), nullable=False),
        sa.Column("assumptions", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["diet_log_id"], ["diet_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diet_macro_items_diet_log_id",
        "diet_macro_items",
        ["diet_log_id"],
        unique=False,
    )

    op.create_table(
        "workout_exercise_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workout_log_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight_lb", sa.Float(), nullable=False),
        sa.Column("workout_type", sa.String(length=64), nullable=False),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.Column("time_minutes", sa.Float(), nullable=True),
        sa.Column("assumption", sa.Text(), nullable=False),
        sa.Column("sport_name", sa.String(length=255), nullable=False),
        sa.Column("calories_burn", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["workout_log_id"], ["workout_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workout_exercise_items_workout_log_id",
        "workout_exercise_items",
        ["workout_log_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workout_exercise_items_workout_log_id", table_name="workout_exercise_items")
    op.drop_table("workout_exercise_items")
    op.drop_index("ix_diet_macro_items_diet_log_id", table_name="diet_macro_items")
    op.drop_table("diet_macro_items")
