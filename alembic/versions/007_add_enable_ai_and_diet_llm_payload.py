"""add enable_ai and diet llm payload

Revision ID: 007_enable_ai_diet_llm
Revises: 006_account_deletion_histories
Create Date: 2026-03-29

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_enable_ai_diet_llm"
down_revision: Union[str, Sequence[str], None] = "006_account_deletion_histories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workout_logs", sa.Column("enable_ai", sa.Boolean(), nullable=True))
    op.add_column("diet_logs", sa.Column("enable_ai", sa.Boolean(), nullable=True))
    op.add_column("diet_logs", sa.Column("llm_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("diet_logs", "llm_payload")
    op.drop_column("diet_logs", "enable_ai")
    op.drop_column("workout_logs", "enable_ai")
