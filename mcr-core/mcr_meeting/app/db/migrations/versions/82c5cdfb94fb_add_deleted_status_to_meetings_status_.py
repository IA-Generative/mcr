"""add deleted status to meetings_status enum

Revision ID: 82c5cdfb94fb
Revises: 9aa89891354a
Create Date: 2026-02-02 17:57:02.322409

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82c5cdfb94fb"
down_revision: Union[str, None] = "9aa89891354a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_options = (
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
)

new_status = "DELETED"

enum_name = "meetingstatus"
meeting_table_name = "meeting"
meeting_transition_record_table_name = "meeting_transition_record"
column_name = "status"
default_value_on_downgrade = "TRANSCRIPTION_FAILED"


def upgrade() -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{new_status}'")
    pass


def downgrade() -> None:
    # delete all entries that had the status 'DELETED' from meeting and meeting_transition_record
    op.execute(
        sa.text(
            f"DELETE FROM {meeting_table_name} WHERE {column_name} = :removed_value"
        ).bindparams(removed_value=new_status)
    )
    op.execute(
        sa.text(
            f"DELETE FROM {meeting_transition_record_table_name} "
            f"WHERE {column_name} = :removed_value"
        ).bindparams(removed_value=new_status)
    )

    # temporarily drop column defaults to avoid DatatypeMismatch from meeting and meeting_transition_record
    op.alter_column(meeting_table_name, column_name, server_default=None)
    op.alter_column(
        meeting_transition_record_table_name, column_name, server_default=None
    )

    # recreate old enum without the removed value
    tmp_enum = sa.Enum(*old_options, name=f"{enum_name}_old")
    tmp_enum.create(op.get_bind(), checkfirst=True)

    # convert meeting.status back to old enum using text casting
    op.alter_column(
        meeting_table_name,
        column_name,
        type_=tmp_enum,
        postgresql_using=f"{column_name}::text::{enum_name}_old",
    )

    # convert meeting_transition_record.status back to old enum using text casting
    op.alter_column(
        meeting_transition_record_table_name,
        column_name,
        type_=tmp_enum,
        postgresql_using=f"{column_name}::text::{enum_name}_old",
    )

    # restore column defaults while the old enum type is still present for meeting and meeting_transition_record
    op.alter_column(
        meeting_table_name,
        column_name,
        server_default=sa.text(f"'{default_value_on_downgrade}'"),
    )
    op.alter_column(
        meeting_transition_record_table_name,
        column_name,
        server_default=sa.text(f"'{default_value_on_downgrade}'"),
    )

    # drop the new enum type (no remaining dependencies)
    op.execute(sa.text(f"DROP TYPE {enum_name}"))

    # rename the old enum back to the original name
    op.execute(sa.text(f"ALTER TYPE {enum_name}_old RENAME TO {enum_name}"))
    pass
