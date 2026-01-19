"""add webcconf to meeting platform

Revision ID: 37e431c19a4d
Revises: bbf0d24b3bc4
Create Date: 2025-10-09 11:33:23.655455

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "37e431c19a4d"
down_revision: Union[str, None] = "bbf0d24b3bc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_options = ("WEBINAIRE", "COMU", "MCR_IMPORT", "MCR_RECORD")

new_options = old_options + ("WEBCONF",)

enum_name = "meetingplatforms"
table_name = "meeting"
column_name = "name_platform"
default_value_on_downgrade = "MCR_IMPORT"


def upgrade() -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS 'WEBCONF'")


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {table_name} "
            f"SET {column_name} = :fallback "
            f"WHERE {column_name} = 'WEBCONF'"
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
