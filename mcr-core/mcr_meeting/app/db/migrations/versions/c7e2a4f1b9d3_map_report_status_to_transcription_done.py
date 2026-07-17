"""map REPORT_* meeting statuses to TRANSCRIPTION_DONE

Revision ID: c7e2a4f1b9d3
Revises: b3f9c1a7d5e2
Create Date: 2026-07-17 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from loguru import logger

# revision identifiers, used by Alembic.
revision: str = "c7e2a4f1b9d3"
down_revision: str | None = "b3f9c1a7d5e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REPORT_STATUSES = ("REPORT_PENDING", "REPORT_DONE", "REPORT_FAILED")


def upgrade() -> None:
    # The report has left the meeting state-machine; its state now lives only on the deliverables.
    # Meetings still stored in a REPORT_* status must fall back to TRANSCRIPTION_DONE, otherwise a
    # later state-machine event (e.g. a re-transcription) would start from a status the SM no longer
    # knows.
    result = op.get_bind().execute(
        sa.text(
            "UPDATE meeting SET status = 'TRANSCRIPTION_DONE' "
            "WHERE status IN ('REPORT_PENDING', 'REPORT_DONE', 'REPORT_FAILED')"
        )
    )
    logger.info("Mapped {} REPORT_* meetings to TRANSCRIPTION_DONE", result.rowcount)


def downgrade() -> None:
    # Irreversible: the original report status is not reconstructable from meeting.status (it lives
    # on the deliverables). Leave the rows in place.
    pass
