"""add deleted status to meetings_status enum

Revision ID: 82c5cdfb94fb
Revises: 9aa89891354a
Create Date: 2026-02-02 17:57:02.322409

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

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
table_name = "meeting"
column_name = "status"
default_value_on_downgrade = "TRANSCRIPTION_FAILED"


def upgrade() -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{new_status}'")
    pass


def downgrade() -> None:
    # delete all entries that had the status 'DELETED'
    op.execute(
        sa.text(
            f"DELETE FROM {table_name} "
            f"WHERE {column_name} = :removed_value"
        ).bindparams(removed_value=new_status)
    )

    # temporarily drop the column default to avoid DatatypeMismatch
    op.alter_column(table_name, column_name, server_default=None)

    # recreate old enum
    tmp_enum = sa.Enum(*old_options, name=f"{enum_name}_old")
    tmp_enum.create(op.get_bind(), checkfirst=True)

    # convert column back to old enum using text casting
    op.alter_column(
        table_name,
        column_name,
        type_=tmp_enum,
        postgresql_using=f"{column_name}::text::{enum_name}_old",
    )

    # drop the new enum type
    op.execute(sa.text(f"DROP TYPE {enum_name}"))

    # rename the old enum back to the original name
    op.execute(sa.text(f"ALTER TYPE {enum_name}_old RENAME TO {enum_name}"))

    # restore the original default
    op.alter_column(
        table_name,
        column_name,
        server_default=sa.text(f"'{default_value_on_downgrade}'"),
    )
