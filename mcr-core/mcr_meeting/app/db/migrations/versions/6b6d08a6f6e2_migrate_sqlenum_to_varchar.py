"""migrate sqlenum to varchar

Revision ID: 6b6d08a6f6e2
Revises: b6b97a4125c5
Create Date: 2026-04-22 17:37:49.503787

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6b6d08a6f6e2"
down_revision: str | None = "b6b97a4125c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Convert ENUM columns to VARCHAR
    op.alter_column(
        "meeting",
        "name_platform",
        existing_type=postgresql.ENUM(
            "WEBINAIRE",
            "COMU",
            "MCR_IMPORT",
            "MCR_RECORD",
            "WEBCONF",
            "VISIO",
            "WEBEX",
            name="meetingplatforms",
        ),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.alter_column(
        "meeting",
        "status",
        existing_type=postgresql.ENUM(
            "NONE",
            "CAPTURE_PENDING",
            "CAPTURE_DONE",
            "CAPTURE_IN_PROGRESS",
            "TRANSCRIPTION_PENDING",
            "TRANSCRIPTION_DONE",
            "CAPTURE_FAILED",
            "TRANSCRIPTION_FAILED",
            "REPORT_PENDING",
            "REPORT_DONE",
            "IMPORT_PENDING",
            "CAPTURE_BOT_IS_CONNECTING",
            "CAPTURE_BOT_CONNECTION_FAILED",
            "TRANSCRIPTION_IN_PROGRESS",
            "DELETED",
            "REPORT_FAILED",
            name="meetingstatus",
        ),
        type_=sa.String(),
        existing_nullable=False,
        server_default=sa.text("'NONE'"),
        existing_server_default=sa.text("'TRANSCRIPTION_DONE'::meetingstatus"),
    )
    op.alter_column(
        "meeting_transition_record",
        "status",
        existing_type=postgresql.ENUM(
            "NONE",
            "CAPTURE_PENDING",
            "CAPTURE_DONE",
            "CAPTURE_IN_PROGRESS",
            "TRANSCRIPTION_PENDING",
            "TRANSCRIPTION_DONE",
            "CAPTURE_FAILED",
            "TRANSCRIPTION_FAILED",
            "REPORT_PENDING",
            "REPORT_DONE",
            "IMPORT_PENDING",
            "CAPTURE_BOT_IS_CONNECTING",
            "CAPTURE_BOT_CONNECTION_FAILED",
            "TRANSCRIPTION_IN_PROGRESS",
            "DELETED",
            "REPORT_FAILED",
            name="meetingstatus",
        ),
        type_=sa.String(),
        server_default=None,
        existing_server_default=sa.text("'TRANSCRIPTION_DONE'::meetingstatus"),
        existing_nullable=False,
    )

    # Drop orphaned PostgreSQL ENUM types
    postgresql.ENUM(name="meetingstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="meetingplatforms").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Recreate PostgreSQL ENUM types
    meetingstatus = postgresql.ENUM(
        "NONE",
        "CAPTURE_PENDING",
        "CAPTURE_DONE",
        "CAPTURE_IN_PROGRESS",
        "TRANSCRIPTION_PENDING",
        "TRANSCRIPTION_DONE",
        "CAPTURE_FAILED",
        "TRANSCRIPTION_FAILED",
        "REPORT_PENDING",
        "REPORT_DONE",
        "IMPORT_PENDING",
        "CAPTURE_BOT_IS_CONNECTING",
        "CAPTURE_BOT_CONNECTION_FAILED",
        "TRANSCRIPTION_IN_PROGRESS",
        "DELETED",
        "REPORT_FAILED",
        name="meetingstatus",
    )
    meetingplatforms = postgresql.ENUM(
        "WEBINAIRE",
        "COMU",
        "MCR_IMPORT",
        "MCR_RECORD",
        "WEBCONF",
        "VISIO",
        "WEBEX",
        name="meetingplatforms",
    )
    meetingstatus.create(op.get_bind(), checkfirst=True)
    meetingplatforms.create(op.get_bind(), checkfirst=True)

    # 1. Drop server defaults that would block the type change
    op.alter_column(
        "meeting",
        "status",
        server_default=None,
        existing_server_default=sa.text("'NONE'"),
        existing_type=sa.String(),
        existing_nullable=False,
    )

    # 2. Convert VARCHAR columns back to ENUM
    op.alter_column(
        "meeting_transition_record",
        "status",
        existing_type=sa.String(),
        type_=meetingstatus,
        existing_nullable=False,
        postgresql_using="status::meetingstatus",
    )
    op.alter_column(
        "meeting",
        "status",
        existing_type=sa.String(),
        type_=meetingstatus,
        existing_nullable=False,
        postgresql_using="status::meetingstatus",
    )
    op.alter_column(
        "meeting",
        "name_platform",
        existing_type=sa.String(),
        type_=meetingplatforms,
        existing_nullable=False,
        postgresql_using="name_platform::meetingplatforms",
    )

    # 3. Restore server defaults with ENUM cast
    op.alter_column(
        "meeting",
        "status",
        server_default=sa.text("'TRANSCRIPTION_DONE'::meetingstatus"),
        existing_type=meetingstatus,
        existing_nullable=False,
    )
    op.alter_column(
        "meeting_transition_record",
        "status",
        server_default=sa.text("'TRANSCRIPTION_DONE'::meetingstatus"),
        existing_type=meetingstatus,
        existing_nullable=False,
    )
