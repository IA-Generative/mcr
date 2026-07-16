from datetime import datetime, timedelta, timezone

from loguru import logger

from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    init_transcription as apply_init_transcription,
)
from mcr_meeting.app.domain.transcription_queue_estimation import (
    estimate_wait_time_minutes,
)
from mcr_meeting.app.infrastructure.celery import (
    enqueue_transcription_pipeline,
    enqueue_transcription_task,
)
from mcr_meeting.app.infrastructure.unleash import FeatureFlag, is_enabled
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases._shared.transcription_deliverable import (
    queue_transcription_deliverable,
)


def _structural_split_enabled() -> bool:
    try:
        return is_enabled(FeatureFlag.STRUCTURAL_SPLIT_ENABLED)
    except Exception as e:
        logger.warning(
            "Failed to read STRUCTURAL_SPLIT_ENABLED, enqueueing legacy task: {}", e
        )
        return False


def init_transcription(meeting_id: int) -> Meeting:
    """Queue a meeting for transcription.

    Called both by the UI (after a capture is done / failed) and by the capture
    worker itself; neither carries an authenticated user, so no ownership check.
    """
    meeting = get_meeting_with_owner(meeting_id)
    apply_init_transcription(meeting)

    if meeting.name_platform == MeetingPlatforms.MCR_RECORD:
        meeting.end_date = datetime.now(timezone.utc)

    enqueue = (
        enqueue_transcription_pipeline
        if _structural_split_enabled()
        else enqueue_transcription_task
    )
    with UnitOfWork():
        update_meeting(meeting)
        queue_transcription_deliverable(meeting.id)
        enqueue(meeting.id, str(meeting.owner.keycloak_uuid))

    waiting_time_minutes = estimate_wait_time_minutes(count_pending_meetings())

    now = datetime.now(timezone.utc)
    with UnitOfWork():
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
