"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-03-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=512), nullable=True),
        sa.Column("apple_user_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("apple_user_id"),
    )
    op.create_index("ix_users_apple_user_id", "users", ["apple_user_id"], unique=False)

    op.create_table(
        "workout_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("local_id", sa.Uuid(), nullable=False),
        sa.Column("created_at_local", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_local", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("transcript_confidence", sa.Float(), nullable=True),
        sa.Column("transcript_locale", sa.String(length=64), nullable=True),
        sa.Column("workout_type", sa.String(length=255), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("intensity", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("calories_estimate", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "local_id", name="uq_workout_user_local"),
    )
    op.create_index("ix_workout_logs_user_id", "workout_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_workout_logs_user_server_updated",
        "workout_logs",
        ["user_id", "server_updated_at"],
        unique=False,
    )

    op.create_table(
        "diet_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("local_id", sa.Uuid(), nullable=False),
        sa.Column("created_at_local", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_local", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("transcript_confidence", sa.Float(), nullable=True),
        sa.Column("transcript_locale", sa.String(length=64), nullable=True),
        sa.Column("meal_type", sa.String(length=255), nullable=True),
        sa.Column("items_text", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("calories_estimate", sa.Float(), nullable=True),
        sa.Column("protein_grams", sa.Float(), nullable=True),
        sa.Column("carbs_grams", sa.Float(), nullable=True),
        sa.Column("fat_grams", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "local_id", name="uq_diet_user_local"),
    )
    op.create_index("ix_diet_logs_user_id", "diet_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_diet_logs_user_server_updated",
        "diet_logs",
        ["user_id", "server_updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_diet_logs_user_server_updated", table_name="diet_logs")
    op.drop_index("ix_diet_logs_user_id", table_name="diet_logs")
    op.drop_table("diet_logs")
    op.drop_index("ix_workout_logs_user_server_updated", table_name="workout_logs")
    op.drop_index("ix_workout_logs_user_id", table_name="workout_logs")
    op.drop_table("workout_logs")
    op.drop_index("ix_users_apple_user_id", table_name="users")
    op.drop_table("users")
