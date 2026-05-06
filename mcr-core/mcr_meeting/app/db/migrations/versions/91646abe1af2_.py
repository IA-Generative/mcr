"""empty message

Revision ID: 91646abe1af2
Revises: d7e3c0f4a8b1, e57b5e520610
Create Date: 2026-05-06 17:41:16.024238

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "91646abe1af2"
down_revision: str | None = ("d7e3c0f4a8b1", "e57b5e520610")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
