from datetime import datetime, timezone

from loguru import logger

from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
    TaskCreationException,
)
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    MCRTranscriptionTasks,
)
from mcr_meeting.app.schemas.report_generation import ReportGenerationResponse
from mcr_meeting.app.services.docx_report_generation_service import (
    generate_docx_decisions_reports_from_template,
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
from mcr_meeting.app.services.report_task_service import save_formatted_report
from mcr_meeting.app.services.s3_service import get_transcription_object_name
from mcr_meeting.app.services.send_email_service import (
    send_report_generation_success_email,
)
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)
from mcr_meeting.app.utils.celery_producer import celery_producer_app


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
            MCRTranscriptionTasks.TRANSCRIBE, args=[meeting.id]
        )

    waiting_time_minutes = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
        meeting.id
    )

    create_transcription_transition_record_with_estimation(
        meeting_id=meeting.id, waiting_time_minutes=waiting_time_minutes
    )

    logger.info(
        "Transcription task created for meeting ID: {} with estimated waiting time: {} minutes",
        meeting.id,
        waiting_time_minutes,
    )


def after_start_report_handler(meeting: Meeting, next_status: MeetingStatus) -> None:
    try:
        if meeting.transcription_filename is None:
            raise NotFoundException("Could not find meeting transcription")

        transcription_object_name = get_transcription_object_name(
            meeting_id=meeting.id, filename=meeting.transcription_filename
        )

        with UnitOfWork():
            update_meeting_status(meeting, next_status)
            celery_producer_app.send_task(
                MCRReportGenerationTasks.REPORT,
                args=[meeting.id, transcription_object_name],
            )

        logger.info("Report generation task created for meeting: {}", meeting.id)

    except Exception as e:
        logger.error("Error creating transcription task: {}", e)
        raise TaskCreationException(str(e))


def after_complete_report_handler(
    meeting: Meeting,
    next_status: MeetingStatus,
    report_response: ReportGenerationResponse,
) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)
        docx_buffer = generate_docx_decisions_reports_from_template(
            report_response, meeting.name
        )
        save_formatted_report(meeting_id=meeting.id, file_like_object=docx_buffer)

    send_report_generation_success_email(meeting_id=meeting.id)


def update_status_handler(meeting: Meeting, next_status: MeetingStatus) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)


def after_transition_handler(meeting_id: int, next_status: MeetingStatus) -> None:
    create_transition_record_service(meeting_id, next_status)
