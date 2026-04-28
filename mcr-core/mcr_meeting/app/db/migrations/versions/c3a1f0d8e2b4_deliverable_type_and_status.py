"""deliverable: rename file_type -> type, add status, backfill

Revision ID: c3a1f0d8e2b4
Revises: 6b6d08a6f6e2
Create Date: 2026-04-28 18:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a1f0d8e2b4"
down_revision: str | None = "6b6d08a6f6e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("deliverable", "file_type", new_column_name="type")

    op.add_column(
        "deliverable",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="PENDING",
        ),
    )

    op.execute("UPDATE deliverable SET type = 'DECISION_RECORD' WHERE type = 'REPORT'")
    # Every pre-existing Deliverable row was created by store_deliverable AFTER
    # a successful Drive upload, so AVAILABLE is correct for all of them.
    op.execute("UPDATE deliverable SET status = 'AVAILABLE'")

    # Orphan backfill: meetings whose report/transcription file lives in S3
    # but never got a Deliverable row (Drive-upload code is mostly dead today,
    # so almost every successful report is an orphan).
    # Lenient selection: trust file-presence; exclude DELETED meetings only.
    # external_url left NULL — Step 2's GET handler falls back to the meeting's
    # *_filename column when external_url IS NULL.
    # NOT EXISTS guard keeps this idempotent and skips "both" rows.
    op.execute(
        """
        DO $$
        DECLARE
            report_count INT;
            transcription_count INT;
        BEGIN
            INSERT INTO deliverable
                (meeting_id, type, status, external_url, created_at, updated_at)
            SELECT m.id, 'DECISION_RECORD', 'AVAILABLE', NULL,
                   m.creation_date, m.creation_date
            FROM meeting m
            WHERE m.report_filename IS NOT NULL
              AND m.status <> 'DELETED'
              AND NOT EXISTS (
                SELECT 1 FROM deliverable d
                WHERE d.meeting_id = m.id
                  AND d.type IN ('DECISION_RECORD', 'DETAILED_SYNTHESIS')
              );
            GET DIAGNOSTICS report_count = ROW_COUNT;
            RAISE NOTICE 'Backfilled % DECISION_RECORD deliverables for orphan reports', report_count;

            INSERT INTO deliverable
                (meeting_id, type, status, external_url, created_at, updated_at)
            SELECT m.id, 'TRANSCRIPTION', 'AVAILABLE', NULL,
                   m.creation_date, m.creation_date
            FROM meeting m
            WHERE m.transcription_filename IS NOT NULL
              AND m.status <> 'DELETED'
              AND NOT EXISTS (
                SELECT 1 FROM deliverable d
                WHERE d.meeting_id = m.id AND d.type = 'TRANSCRIPTION'
              );
            GET DIAGNOSTICS transcription_count = ROW_COUNT;
            RAISE NOTICE 'Backfilled % TRANSCRIPTION deliverables for orphan transcriptions', transcription_count;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE deliverable SET type = 'REPORT' "
        "WHERE type IN ('DECISION_RECORD', 'DETAILED_SYNTHESIS')"
    )
    op.drop_column("deliverable", "status")
    op.alter_column("deliverable", "type", new_column_name="file_type")
