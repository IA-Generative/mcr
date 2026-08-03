"""create deliverable_feedback_reason table

Revision ID: b41d7e9c8f52
Revises: f8a3c1b70d24
Create Date: 2026-07-31 09:41:02.887413

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b41d7e9c8f52"
down_revision: str | None = "f8a3c1b70d24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deliverable_feedback_reason",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("deliverable_feedback_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["deliverable_feedback_id"],
            ["deliverable_feedback.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("deliverable_feedback_reason")
