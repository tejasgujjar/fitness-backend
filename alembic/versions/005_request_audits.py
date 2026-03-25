"""request audits table

Revision ID: 005_request_audits
Revises: 004_add_workout_llm_payload
Create Date: 2026-03-24

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_request_audits"
down_revision: Union[str, Sequence[str], None] = "004_add_workout_llm_payload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_audits",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("query_string", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("request_headers", sa.JSON(), nullable=True),
        sa.Column("response_headers", sa.JSON(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index("ix_request_audits_user_id", "request_audits", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_request_audits_user_id", table_name="request_audits")
    op.drop_table("request_audits")
