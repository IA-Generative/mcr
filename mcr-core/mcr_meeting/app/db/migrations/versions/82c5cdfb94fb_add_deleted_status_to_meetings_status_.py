"""add deleted status to meetings_status enum

Revision ID: 82c5cdfb94fb
Revises: 9aa89891354a
Create Date: 2026-02-02 17:57:02.322409

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82c5cdfb94fb"
down_revision: Union[str, None] = "9aa89891354a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS 'DELETED'")
    pass


def downgrade() -> None:
    # No clean way to remove an item from an enum in postgres.
    pass
