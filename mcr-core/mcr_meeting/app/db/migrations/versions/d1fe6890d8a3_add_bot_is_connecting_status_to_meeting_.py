"""add bot is connecting status to meeting status

Revision ID: d1fe6890d8a3
Revises: ac554ef33c48
Create Date: 2025-09-25 09:46:09.107055

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1fe6890d8a3"
down_revision: Union[str, None] = "ac554ef33c48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_options = (
    "NONE",
    "CAPTURE_PENDING",
    "CAPTURE_IN_PROGRESS",
    "TRANSCRIPTION_PENDING",
    "TRANSCRIPTION_DONE",
    "CAPTURE_FAILED",
    "TRANSCRIPTION_FAILED",
    "REPORT_PENDING",
    "REPORT_DONE",
    "IMPORT_PENDING",
)

enum_name = "meetingstatus"
table_name = "meeting"
column_name = "status"
default_value_on_downgrade = "TRANSCRIPTION_PENDING"


def upgrade() -> None:
    enum_name = "meetingstatus"
    op.execute(
        f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS 'CAPTURE_BOT_IS_CONNECTING'"
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {table_name} "
            f"SET {column_name} = :fallback "
            f"WHERE {column_name} = 'CAPTURE_BOT_IS_CONNECTING'"
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
