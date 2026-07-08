"""backfill TRANSCRIPTION and report deliverables for all historical meetings

Revision ID: b3f9c1a7d5e2
Revises: 0781ae1c037a
Create Date: 2026-07-03 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from loguru import logger

# revision identifiers, used by Alembic.
revision: str = "b3f9c1a7d5e2"
down_revision: str | None = "0781ae1c037a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

meeting = sa.table(
    "meeting",
    sa.column("id", sa.Integer),
    sa.column("transcription_filename", sa.String),
    sa.column("report_filename", sa.String),
    sa.column("creation_date", sa.DateTime),
)
meeting_transition_record = sa.table(
    "meeting_transition_record",
    sa.column("meeting_id", sa.Integer),
    sa.column("timestamp", sa.DateTime),
    sa.column("status", sa.String),
)
deliverable = sa.table(
    "deliverable",
    sa.column("meeting_id", sa.Integer),
    sa.column("type", sa.String),
    sa.column("status", sa.String),
    sa.column("external_url", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)

_INSERT_COLUMNS = [
    "meeting_id",
    "type",
    "status",
    "external_url",
    "created_at",
    "updated_at",
]


def _already_has(
    deliverable_type_filter: sa.ColumnElement[bool],
) -> sa.ColumnElement[bool]:
    # Matches uq_deliverable_meeting_type_active (WHERE status <> 'DELETED'), so each INSERT is a
    # no-op on rows already covered by earlier backfills -- keeps this migration idempotent.
    return sa.exists().where(
        sa.and_(
            deliverable.c.meeting_id == meeting.c.id,
            deliverable_type_filter,
            deliverable.c.status != "DELETED",
        )
    )


def transcription_backfill() -> sa.Insert:
    # Evidence is a TRANSCRIPTION_DONE transition; created_at uses its (always non-null) timestamp.
    done = (
        sa.select(
            meeting_transition_record.c.meeting_id,
            sa.func.max(meeting_transition_record.c.timestamp).label("done_at"),
        )
        .where(meeting_transition_record.c.status == "TRANSCRIPTION_DONE")
        .group_by(meeting_transition_record.c.meeting_id)
        .subquery("t")
    )
    select = (
        sa.select(
            meeting.c.id,
            sa.literal("TRANSCRIPTION"),
            sa.literal("AVAILABLE"),
            sa.null(),
            done.c.done_at,
            done.c.done_at,
        )
        .select_from(meeting.join(done, done.c.meeting_id == meeting.c.id))
        .where(
            sa.and_(
                meeting.c.transcription_filename.is_not(None),
                sa.not_(_already_has(deliverable.c.type == "TRANSCRIPTION")),
            )
        )
    )
    return deliverable.insert().from_select(_INSERT_COLUMNS, select)


def report_backfill() -> sa.Insert:
    # The legacy model stored one report blob (report_filename) and meeting_transition_record only
    # records a type-agnostic REPORT_DONE, so the only faithful reconstruction is DECISION_RECORD
    # (the legacy default), timestamped by creation_date -- same choice as c3a1f0d8e2b4.
    # creation_date is nullable but deliverable.created_at is NOT NULL, so COALESCE to now() for
    # the rare legacy rows that lack it (the value is irrelevant to the success panels, which
    # filter on meeting.creation_date). The guard spans every report type (type <> 'TRANSCRIPTION')
    # so we never add a redundant DECISION_RECORD when a DETAILED_SYNTHESIS/CUSTOM_REPORT exists.
    created_at = sa.func.coalesce(meeting.c.creation_date, sa.func.now())
    select = sa.select(
        meeting.c.id,
        sa.literal("DECISION_RECORD"),
        sa.literal("AVAILABLE"),
        sa.null(),
        created_at,
        created_at,
    ).where(
        sa.and_(
            meeting.c.report_filename.is_not(None),
            sa.not_(_already_has(deliverable.c.type != "TRANSCRIPTION")),
        )
    )
    return deliverable.insert().from_select(_INSERT_COLUMNS, select)


def upgrade() -> None:
    # Reconcile history to the invariant "a meeting with success evidence has an AVAILABLE
    # deliverable of the matching kind", so the deliverable-existence success panels are correct.
    # Not windowed and status-agnostic on purpose: we key on the invariant, not on a cohort
    # (recent / DELETED / old). Running it before the planned auto-delete means those meetings
    # already own their deliverables when soft-deleted, and deliverables persist through
    # soft-delete. Supersedes the narrower c3a1f0d8e2b4 / d2c7b9a4e1f8 backfills, which excluded
    # DELETED meetings (report) or only covered the last 30 days (transcription). external_url
    # stays NULL (Step 2's GET falls back to the meeting's *_filename).
    bind = op.get_bind()
    result = bind.execute(transcription_backfill())
    logger.info(
        "Backfilled {} TRANSCRIPTION deliverables (all history)", result.rowcount
    )
    result = bind.execute(report_backfill())
    logger.info(
        "Backfilled {} DECISION_RECORD deliverables (all history)", result.rowcount
    )


def downgrade() -> None:
    # Data-only backfill; leave the rows in place on downgrade (matches d2c7b9a4e1f8).
    pass
