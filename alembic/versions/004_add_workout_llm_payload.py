"""add llm_payload column to workout_logs

Revision ID: 004_add_workout_llm_payload
Revises: 003_add_created_at_columns
Create Date: 2026-03-23

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_add_workout_llm_payload"
down_revision: Union[str, Sequence[str], None] = "003_add_created_at_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workout_logs", sa.Column("llm_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("workout_logs", "llm_payload")
