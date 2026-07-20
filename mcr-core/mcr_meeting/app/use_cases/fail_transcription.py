from datetime import datetime, timezone

from mcr_meeting.app.db.deliverable_repository import (
    find_requested_reports_by_meeting,
    get_active_by_meeting_and_type,
    save_deliverable,
)
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.deliverable_transitions import mark_failed
from mcr_meeting.app.domain.meeting_transitions import (
    fail_transcription as apply_fail_transcription,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def fail_transcription(meeting_id: int) -> Meeting:
    """Mark a meeting's transcription as failed. Called by the transcription
    worker; no authenticated user.

    The ``TRANSCRIPTION_FAILED`` transition record is written here, atomically
    with the status update; the state machine no longer records it (this status
    is drained from its ``after_transition`` hook).
    """
    meeting = get_meeting_by_id(meeting_id)
    apply_fail_transcription(meeting)

    deliverable = get_active_by_meeting_and_type(
        meeting_id=meeting.id, deliverable_type=DeliverableType.TRANSCRIPTION
    )

    with UnitOfWork():
        update_meeting(meeting)
        mark_failed(deliverable)
        for report in find_requested_reports_by_meeting(meeting.id):
            mark_failed(report)
            save_deliverable(report)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=MeetingStatus.TRANSCRIPTION_FAILED,
            )
        )

    return meeting
