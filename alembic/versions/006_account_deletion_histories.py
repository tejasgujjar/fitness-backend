"""account deletion histories

Revision ID: 006_account_deletion_histories
Revises: 005_request_audits
Create Date: 2026-03-28

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_account_deletion_histories"
down_revision: Union[str, Sequence[str], None] = "005_request_audits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_deletion_histories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=512), nullable=True),
        sa.Column("apple_user_id", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("trigger", sa.String(length=64), server_default=sa.text("'self_service'"), nullable=False),
        sa.Column("workout_logs_deleted_count", sa.Integer(), nullable=False),
        sa.Column("diet_logs_deleted_count", sa.Integer(), nullable=False),
        sa.Column("app_version", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=1024), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_deletion_histories_user_id",
        "account_deletion_histories",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_account_deletion_histories_user_id", table_name="account_deletion_histories")
    op.drop_table("account_deletion_histories")
