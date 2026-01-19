"""add capture_end status

Revision ID: e4d8594ebbcf
Revises: 2eff96979526
Create Date: 2025-12-17 15:42:22.199755

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4d8594ebbcf"
down_revision: Union[str, None] = "2eff96979526"
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
    "CAPTURE_BOT_IS_CONNECTING",
    "CAPTURE_BOT_CONNECTION_FAILED",
    "TRANSCRIPTION_IN_PROGRESS",
)

new_status = "CAPTURE_DONE"

enum_name = "meetingstatus"
table_name = "meeting"
column_name = "status"
default_value_on_downgrade = "TRANSCRIPTION_PENDING"


def upgrade() -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{new_status}'")

    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {table_name} "
            f"SET {column_name} = :fallback "
            f"WHERE {column_name} = '{new_status}'"
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
    pass
    # ### end Alembic commands ###
