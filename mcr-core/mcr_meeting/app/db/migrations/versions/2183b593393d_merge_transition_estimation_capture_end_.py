"""merge_transition_estimation_capture_end_status

Revision ID: 2183b593393d
Revises: 3b6b37018db1, e4d8594ebbcf
Create Date: 2025-12-23 13:42:50.332448

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "2183b593393d"
down_revision: Union[str, None] = ("3b6b37018db1", "e4d8594ebbcf")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
