"""add meeting_transition_record (meeting_id,timestamp) and meeting.user_id indexes

Revision ID: 0781ae1c037a
Revises: d2c7b9a4e1f8
Create Date: 2026-07-03 13:37:46.413860

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0781ae1c037a"
down_revision: str | None = "d2c7b9a4e1f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(op.f("ix_meeting_user_id"), "meeting", ["user_id"], unique=False)
    op.create_index(
        "ix_meeting_transition_record_meeting_id_timestamp",
        "meeting_transition_record",
        ["meeting_id", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meeting_transition_record_meeting_id_timestamp",
        table_name="meeting_transition_record",
    )
    op.drop_index(op.f("ix_meeting_user_id"), table_name="meeting")
