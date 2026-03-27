"""add webex to meeting platform

Revision ID: a64618d27ac5
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18 16:55:10.243915

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a64618d27ac5"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


old_options = ("WEBINAIRE", "COMU", "MCR_IMPORT", "MCR_RECORD", "WEBCONF", "VISIO")

new_options = old_options + ("WEBEX",)

enum_name = "meetingplatforms"
table_name = "meeting"
column_name = "name_platform"
default_value_on_downgrade = "MCR_IMPORT"


def upgrade() -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS 'WEBEX'")


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {table_name} "
            f"SET {column_name} = :fallback "
            f"WHERE {column_name} = 'WEBEX'"
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
