from datetime import datetime, timedelta, timezone

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    start_transcription as apply_start_transcription,
)
from mcr_meeting.app.domain.transcription_queue_estimation import (
    estimate_transcription_duration_minutes,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases._shared.transcription_deliverable import (
    start_transcription_deliverable,
)


def start_transcription(meeting_id: int) -> Meeting:
    """Mark a meeting's transcription as started. Called by the transcription
    worker; no authenticated user."""
    meeting = get_meeting_by_id(meeting_id)
    apply_start_transcription(meeting)

    waiting_time_minutes = estimate_transcription_duration_minutes(
        meeting.duration_minutes
    )
    now = datetime.now(timezone.utc)
    with UnitOfWork():
        update_meeting(meeting)
        start_transcription_deliverable(meeting.id)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=now,
                predicted_date_of_next_transition=now
                + timedelta(minutes=waiting_time_minutes),
                status=meeting.status,
            )
        )

    return meeting
