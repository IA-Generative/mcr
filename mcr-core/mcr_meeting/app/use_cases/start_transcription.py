from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    start_transcription as apply_start_transcription,
)
from mcr_meeting.app.domain.transcription_queue_estimation import (
    estimate_transcription_duration_minutes,
)
from mcr_meeting.app.infrastructure.analytics import record_predicted_transition
from mcr_meeting.app.models import Meeting


def start_transcription(meeting_id: int) -> Meeting:
    """Mark a meeting's transcription as started. Called by the transcription
    worker; no authenticated user."""
    meeting = get_meeting_by_id(meeting_id)
    apply_start_transcription(meeting)

    with UnitOfWork():
        update_meeting(meeting)

    waiting_time_minutes = estimate_transcription_duration_minutes(
        meeting.duration_minutes
    )
    record_predicted_transition(
        meeting_id=meeting.id,
        status=meeting.status,
        waiting_time_minutes=waiting_time_minutes,
    )

    return meeting
