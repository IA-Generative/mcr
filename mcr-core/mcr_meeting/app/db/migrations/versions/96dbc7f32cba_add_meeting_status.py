"""add_meeting_status

Revision ID: 96dbc7f32cba
Revises: ed12f9c61fe4
Create Date: 2025-08-22 11:59:25.186344

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "96dbc7f32cba"
down_revision: Union[str, None] = "ca74396de706"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old and new definitions for reference (not strictly needed)

old_statuses = (
    "NONE",
    "CAPTURE_PENDING",
    "CAPTURE_IN_PROGRESS",
    "TRANSCRIPTION_PENDING",
    "TRANSCRIPTION_DONE",
    "CAPTURE_FAILED",
    "TRANSCRIPTION_FAILED",
)

new_statuses = sorted(old_statuses + ("REPORT_PENDING", "REPORT_DONE"))

old_meeting_status = sa.Enum(
    *old_statuses,
    name="meetingstatus",
)

new_meeting_status = sa.Enum(
    *new_statuses,
    name="meetingstatus",
)


def upgrade() -> None:
    # Alembic helper for PostgreSQL enum extension
    op.execute("ALTER TYPE meetingstatus ADD VALUE 'REPORT_PENDING'")
    op.execute("ALTER TYPE meetingstatus ADD VALUE 'REPORT_DONE'")


def downgrade() -> None:
    meeting = sa.sql.table(
        "meeting", sa.Column("status", new_meeting_status, nullable=False)
    )
    op.get_bind().execute(
        meeting.update()
        .where(
            sa.or_(
                meeting.c.status == "REPORT_PENDING", meeting.c.status == "REPORT_DONE"
            )
        )
        .values(status="TRANSCRIPTION_DONE")
    )

    # Rename current type & remove defautlts
    op.execute("ALTER TYPE meetingstatus RENAME TO meetingstatus_new")
    op.alter_column("meeting", "status", server_default=None)

    # Recreate old type without REPORT_PENDING/REPORT_DONE
    old_meeting_status.create(op.get_bind(), checkfirst=True)  # type: ignore

    # Alter column to cast to the old type
    op.execute(
        "ALTER TABLE meeting ALTER COLUMN status TYPE meetingstatus USING status::text::meetingstatus"
    )
    op.alter_column("meeting", "status")

    # Drop the old renamed type
    op.execute("DROP TYPE meetingstatus_new")
