from datetime import datetime, timezone

from loguru import logger

from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.infrastructure.celery import celery_producer_app
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.schemas.celery_types import (
    MCRTranscriptionTasks,
)
from mcr_meeting.app.schemas.report_generation import (
    ReportResponse,
)
from mcr_meeting.app.services.deliverable_storage_service import store_deliverable
from mcr_meeting.app.services.email.email_service import (
    send_report_generation_success_email,
    send_transcription_generation_success_email,
)
from mcr_meeting.app.services.meeting_service import (
    update_meeting_end_date,
    update_meeting_start_date,
    update_meeting_status,
)
from mcr_meeting.app.services.meeting_transition_record_service import (
    create_transcription_transition_record_with_estimation,
    create_transition_record_service,
)
from mcr_meeting.app.services.report_task_service import persist_report_docx
from mcr_meeting.app.services.transcription_task_service import (
    retrieve_or_create_formatted_docx_transcription,
)
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)


def after_start_capture_bot_handler(
    meeting: Meeting, next_status: MeetingStatus
) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)
        update_meeting_start_date(meeting, datetime.now(timezone.utc))


def after_complete_capture_handler(
    meeting: Meeting, next_status: MeetingStatus
) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)
        update_meeting_end_date(meeting, datetime.now(timezone.utc))


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


def after_complete_transcription_handler(
    meeting: Meeting, next_status: MeetingStatus
) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)

    try:
        docx_buffer = retrieve_or_create_formatted_docx_transcription(meeting)
        store_deliverable(
            meeting_id=meeting.id,
            user_keycloak_uuid=str(meeting.owner.keycloak_uuid),
            file_bytes=docx_buffer.getvalue(),
            type=DeliverableType.TRANSCRIPTION,
            filename=f"Transcription_{meeting.name}.docx",
        )
    except Exception:
        logger.exception(
            "Failed to upload transcription to Drive for meeting {}", meeting.id
        )

    send_transcription_generation_success_email(meeting_id=meeting.id)


def after_complete_report_handler(
    meeting: Meeting,
    next_status: MeetingStatus,
    report_response: ReportResponse,
) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)
        persist_report_docx(meeting_id=meeting.id, report_response=report_response)

    send_report_generation_success_email(meeting_id=meeting.id)


def update_status_handler(meeting: Meeting, next_status: MeetingStatus) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)


def after_transition_handler(meeting_id: int, next_status: MeetingStatus) -> None:
    create_transition_record_service(meeting_id, next_status)
