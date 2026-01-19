"""add_import_pending_status

Revision ID: ac554ef33c48
Revises: 96dbc7f32cba
Create Date: 2025-09-09 14:14:04.399138

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac554ef33c48"
down_revision: Union[str, None] = "96dbc7f32cba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_options = (
    "NONE",
    "CAPTURE_PENDING",
    "CAPTURE_IN_PROGRESS",
    "TRANSCRIPTION_PENDING",
    "TRANSCRIPTION_DONE",
    "REPORT_PENDING",
    "REPORT_DONE",
    "CAPTURE_FAILED",
    "TRANSCRIPTION_FAILED",
)
new_options = old_options + ("IMPORT_PENDING",)

enum_name = "meetingstatus"
table_name = "meeting"
column_name = "status"
default_value_on_downgrade = "CAPTURE_FAILED"


def upgrade() -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS 'IMPORT_PENDING'")


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {table_name} "
            f"SET {column_name} = :fallback "
            f"WHERE {column_name} = 'IMPORT_PENDING'"
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
