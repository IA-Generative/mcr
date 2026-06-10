"""backfill TRANSCRIPTION deliverables for meetings completed in the last 30 days

Revision ID: d2c7b9a4e1f8
Revises: 91646abe1af2
Create Date: 2026-06-05 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2c7b9a4e1f8"
down_revision: str | None = "91646abe1af2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The transcription-success flow now always creates a TRANSCRIPTION deliverable,
    # but earlier flows only did so on a successful Drive upload. Backfill rows for
    # meetings that recently reached TRANSCRIPTION_DONE so the frontend tile/links are
    # consistent. created_at/updated_at use the actual transition timestamp.
    # external_url stays NULL; the NOT EXISTS guard matches the partial unique index
    # (meeting_id, type WHERE status <> 'DELETED') and keeps this idempotent.
    op.execute(
        """
        DO $$
        DECLARE
            inserted_count INT;
        BEGIN
            INSERT INTO deliverable
                (meeting_id, type, status, external_url, created_at, updated_at)
            SELECT m.id, 'TRANSCRIPTION', 'AVAILABLE', NULL, t.done_at, t.done_at
            FROM meeting m
            JOIN (
                SELECT meeting_id, MAX(timestamp) AS done_at
                FROM meeting_transition_record
                WHERE status = 'TRANSCRIPTION_DONE'
                GROUP BY meeting_id
            ) t ON t.meeting_id = m.id
            WHERE t.done_at >= NOW() - INTERVAL '30 days'
              AND m.transcription_filename IS NOT NULL
              AND m.status <> 'DELETED'
              AND NOT EXISTS (
                  SELECT 1 FROM deliverable d
                  WHERE d.meeting_id = m.id
                    AND d.type = 'TRANSCRIPTION'
                    AND d.status <> 'DELETED'
              );
            GET DIAGNOSTICS inserted_count = ROW_COUNT;
            RAISE NOTICE 'Backfilled % TRANSCRIPTION deliverables (last 30 days)', inserted_count;
        END $$;
        """
    )


def downgrade() -> None:
    # Data-only backfill; leave the rows in place on downgrade (matches c3a1f0d8e2b4).
    pass
