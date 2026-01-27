"""add report failed status

Revision ID: f45845aa91c0
Revises: 9aa89891354a
Create Date: 2026-01-27 15:54:29.533489

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f45845aa91c0"
down_revision: Union[str, None] = "9aa89891354a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_options = (
    "NONE",
    "CAPTURE_PENDING",
    "CAPTURE_IN_PROGRESS",
    "TRANSCRIPTION_PENDING",
    "TRANSCRIPTION_IN_PROGRESS",
    "TRANSCRIPTION_DONE",
    "CAPTURE_FAILED",
    "TRANSCRIPTION_FAILED",
    "REPORT_PENDING",
    "REPORT_DONE",
    "IMPORT_PENDING",
    "CAPTURE_BOT_IS_CONNECTING",
    "CAPTURE_BOT_CONNECTION_FAILED",
)

new_options = old_options + ("REPORT_FAILED",)

enum_name = "meetingstatus"
table_name = "meeting"
column_name = "status"
default_value_on_downgrade = "TRANSCRIPTION_DONE"

def upgrade() -> None:
    op.execute(
        f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS 'TRANSCRIPTION_IN_PROGRESS'"
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {table_name} "
            f"SET {column_name} = :fallback "
            f"WHERE {column_name} = 'REPORT_FAILED'"
        ).bindparams(fallback=default_value_on_downgrade)
    )

    tmp_enum = sa.Enum(*old_options, name=f"{enum_name}_old")
    tmp_enum.create(op.get_bind(), checkfirst=True)  # type: ignore

    # Alter column to use the temporary enum
    op.alter_column(
        table_name,
        column_name,
        type_=tmp_enum,
        postgresql_using=f"{column_name}::text::{enum_name}_old",
    )

    # Drop the new enum and rename the old one back
    op.execute(f"DROP TYPE {enum_name}")
    op.execute(f"ALTER TYPE {enum_name}_old RENAME TO {enum_name}")
