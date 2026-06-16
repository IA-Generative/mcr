from datetime import datetime, timezone

from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def create_transition_record_service(
    meeting_id: int,
    next_status: MeetingStatus,
) -> None:
    status_with_special_transition_record_handlers = [
        MeetingStatus.CAPTURE_PENDING,
        MeetingStatus.CAPTURE_IN_PROGRESS,
        MeetingStatus.CAPTURE_DONE,
        MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED,
        MeetingStatus.TRANSCRIPTION_PENDING,
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        MeetingStatus.TRANSCRIPTION_DONE,
        MeetingStatus.TRANSCRIPTION_FAILED,
        MeetingStatus.REPORT_PENDING,
        MeetingStatus.REPORT_DONE,
        MeetingStatus.REPORT_FAILED,
    ]

    if next_status in status_with_special_transition_record_handlers:
        return

    record_meeting_transition(meeting_id, next_status)


def record_meeting_transition(meeting_id: int, status: MeetingStatus) -> None:
    """Persist a transition record unconditionally. Use this from a use-case when the
    transition is one the state machine deliberately leaves to the caller."""
    transition_record = MeetingTransitionRecord(
        meeting_id=meeting_id,
        timestamp=datetime.now(timezone.utc),
        status=status,
    )

    with UnitOfWork():
        save_meeting_transition_record(transition_record)
