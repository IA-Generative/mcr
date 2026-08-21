"""create deliverable_feedback table and drop dead deliverable vote columns

Revision ID: f8a3c1b70d24
Revises: 26c0970cb677
Create Date: 2026-07-29 10:12:33.104512

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a3c1b70d24"
down_revision: str | None = "26c0970cb677"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deliverable_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("deliverable_id", sa.Integer(), nullable=False),
        sa.Column("vote_type", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["deliverable_id"], ["deliverable.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deliverable_id"),
    )
    op.drop_column("deliverable", "vote_comment")
    op.drop_column("deliverable", "vote_type")


def downgrade() -> None:
    op.add_column("deliverable", sa.Column("vote_type", sa.String(), nullable=True))
    op.add_column("deliverable", sa.Column("vote_comment", sa.String(), nullable=True))
    op.drop_table("deliverable_feedback")
