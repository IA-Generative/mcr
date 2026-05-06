"""deliverable: dedupe + partial unique index on (meeting_id, type) where active

Revision ID: d7e3c0f4a8b1
Revises: c3a1f0d8e2b4
Create Date: 2026-05-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e3c0f4a8b1"
down_revision: str | None = "c3a1f0d8e2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEX_NAME = "uq_deliverable_meeting_type_active"


def upgrade() -> None:
    # Dedupe before adding the partial unique index: keep the most-recently
    # updated active row per (meeting_id, type), soft-delete the rest.
    op.execute(
        """
        WITH ranked AS (
          SELECT id,
                 ROW_NUMBER() OVER (
                   PARTITION BY meeting_id, type
                   ORDER BY updated_at DESC, id DESC
                 ) AS rn
          FROM deliverable
          WHERE status <> 'DELETED'
        )
        UPDATE deliverable
        SET status = 'DELETED', updated_at = now()
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )

    op.create_index(
        INDEX_NAME,
        "deliverable",
        ["meeting_id", "type"],
        unique=True,
        postgresql_where=sa.text("status <> 'DELETED'"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="deliverable")
