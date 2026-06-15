from datetime import datetime, timezone

from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.infrastructure.celery import celery_producer_app
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.schemas.celery_types import (
    MCRTranscriptionTasks,
)
from mcr_meeting.app.services.meeting_service import (
    update_meeting_end_date,
    update_meeting_status,
)
from mcr_meeting.app.services.meeting_transition_record_service import (
    create_transcription_transition_record_with_estimation,
    create_transition_record_service,
)
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)


def after_init_transcription_handler(
    meeting: Meeting, next_status: MeetingStatus
) -> None:
    with UnitOfWork():
        if meeting.name_platform == MeetingPlatforms.MCR_RECORD:
            update_meeting_end_date(meeting, datetime.now(timezone.utc))

        update_meeting_status(meeting, next_status)
        celery_producer_app.send_task(
            MCRTranscriptionTasks.TRANSCRIBE,
            args=[meeting.id, str(meeting.owner.keycloak_uuid)],
        )

    current_wait_time_minutes = (
        TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
    )

    create_transcription_transition_record_with_estimation(
        meeting_id=meeting.id,
        meeting_status=next_status,
        waiting_time_minutes=current_wait_time_minutes,
    )


def after_start_transcription_handler(
    meeting: Meeting, next_status: MeetingStatus
) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)

    waiting_time_minutes = (
        TranscriptionQueueEstimationService.estimate_transcription_duration_minutes(
            meeting.id
        )
    )

    create_transcription_transition_record_with_estimation(
        meeting_id=meeting.id,
        meeting_status=next_status,
        waiting_time_minutes=waiting_time_minutes,
    )


def update_status_handler(meeting: Meeting, next_status: MeetingStatus) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)


def after_transition_handler(meeting_id: int, next_status: MeetingStatus) -> None:
    create_transition_record_service(meeting_id, next_status)
