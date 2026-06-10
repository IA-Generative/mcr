from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    fail_transcription as apply_fail_transcription,
)
from mcr_meeting.app.models import Meeting


def fail_transcription(meeting_id: int) -> Meeting:
    """Mark a meeting's transcription as failed. Called by the transcription
    worker; no authenticated user.

    The ``TRANSCRIPTION_FAILED`` transition record is written by the state
    machine's ``after_transition`` hook.
    """
    meeting = get_meeting_by_id(meeting_id)
    apply_fail_transcription(meeting)

    with UnitOfWork():
        update_meeting(meeting)

    return meeting
