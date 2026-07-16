from datetime import datetime, timezone

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    fail_transcription as apply_fail_transcription,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases._shared.transcription_deliverable import (
    fail_transcription_deliverable,
)


def fail_transcription(meeting_id: int) -> Meeting:
    """Mark a meeting's transcription as failed. Called by the transcription
    worker; no authenticated user.

    The ``TRANSCRIPTION_FAILED`` transition record is written here, atomically
    with the status update; the state machine no longer records it (this status
    is drained from its ``after_transition`` hook).
    """
    meeting = get_meeting_by_id(meeting_id)
    apply_fail_transcription(meeting)

    with UnitOfWork():
        update_meeting(meeting)
        fail_transcription_deliverable(meeting.id)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=MeetingStatus.TRANSCRIPTION_FAILED,
            )
        )

    return meeting
