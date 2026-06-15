from datetime import datetime, timezone

from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    init_transcription as apply_init_transcription,
)
from mcr_meeting.app.domain.transcription_queue_estimation import (
    estimate_wait_time_minutes,
)
from mcr_meeting.app.infrastructure.analytics import record_predicted_transition
from mcr_meeting.app.infrastructure.celery import enqueue_transcription_task
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_model import MeetingPlatforms


def init_transcription(meeting_id: int) -> Meeting:
    """Queue a meeting for transcription.

    Called both by the UI (after a capture is done / failed) and by the capture
    worker itself; neither carries an authenticated user, so no ownership check.
    """
    meeting = get_meeting_with_owner(meeting_id)
    apply_init_transcription(meeting)

    if meeting.name_platform == MeetingPlatforms.MCR_RECORD:
        meeting.end_date = datetime.now(timezone.utc)

    with UnitOfWork():
        update_meeting(meeting)

    enqueue_transcription_task(meeting.id, str(meeting.owner.keycloak_uuid))
    waiting_time_minutes = estimate_wait_time_minutes(count_pending_meetings())

    with UnitOfWork():
        record_predicted_transition(
            meeting_id=meeting.id,
            status=meeting.status,
            waiting_time_minutes=waiting_time_minutes,
        )

    return meeting
