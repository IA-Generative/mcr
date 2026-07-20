from collections.abc import Sequence
from datetime import datetime, timezone

from loguru import logger

from mcr_meeting.app.db.deliverable_repository import (
    find_requested_reports_by_meeting,
    get_active_by_meeting_and_type,
    save_deliverable,
)
from mcr_meeting.app.db.meeting_repository import (
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.deliverable_transitions import dispatch, mark_available
from mcr_meeting.app.domain.email import (
    build_transcription_ready_email,
)
from mcr_meeting.app.domain.meeting_transitions import mark_transcription_done
from mcr_meeting.app.domain.transcription_rendering import (
    HasSpeakerTranscription,
    render_transcription_docx,
)
from mcr_meeting.app.infrastructure import email as email_infra
from mcr_meeting.app.infrastructure.celery import celery_producer_app
from mcr_meeting.app.infrastructure.s3 import (
    get_transcription_object_name,
    read_full_transcript,
    upload_transcription_to_s3,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.celery_types import MCRReportGenerationTasks
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
from mcr_meeting.app.use_cases._shared.drive_upload import (
    try_upload_deliverable_to_drive,
)
from mcr_meeting.app.use_cases._shared.report_dispatch import (
    REPORT_TYPE_BY_DELIVERABLE,
    build_report_task_kwargs,
)

TRANSCRIPTION_FILENAME = "v0.docx"


def complete_transcription(
    meeting_id: int, transcriptions: list[SpeakerTranscription] | None = None
) -> None:
    meeting = get_meeting_with_owner(meeting_id)
    mark_transcription_done(meeting)

    deliverable = get_active_by_meeting_and_type(
        meeting_id=meeting.id, deliverable_type=DeliverableType.TRANSCRIPTION
    )

    segments: Sequence[HasSpeakerTranscription] = (
        transcriptions
        if transcriptions is not None
        else read_full_transcript(meeting_id).segments
    )
    docx_buffer = render_transcription_docx(meeting.name, segments)
    upload_transcription_to_s3(
        meeting_id=meeting.id,
        filename=TRANSCRIPTION_FILENAME,
        content=docx_buffer,
    )
    meeting.transcription_filename = TRANSCRIPTION_FILENAME

    external_url = try_upload_deliverable_to_drive(
        meeting, DeliverableType.TRANSCRIPTION, docx_buffer.getvalue()
    )

    with UnitOfWork():
        update_meeting(meeting)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=MeetingStatus.TRANSCRIPTION_DONE,
            )
        )
        mark_available(deliverable, external_url)
        _drain_requested_reports(meeting)

    _notify_transcription_ready_best_effort(meeting)


def _drain_requested_reports(meeting: Meeting) -> None:
    transcription_object_name = get_transcription_object_name(
        meeting_id=meeting.id, filename=TRANSCRIPTION_FILENAME
    )
    for report in find_requested_reports_by_meeting(meeting.id):
        dispatch(report)
        save_deliverable(report)
        celery_producer_app.send_task(
            MCRReportGenerationTasks.REPORT,
            args=[
                meeting.id,
                transcription_object_name,
                REPORT_TYPE_BY_DELIVERABLE[report.type],
            ],
            kwargs=build_report_task_kwargs(meeting, report),
        )


def _notify_transcription_ready_best_effort(meeting: Meeting) -> None:
    try:
        content = build_transcription_ready_email(
            meeting.name or "", meeting_id=meeting.id
        )
        email_infra.send_email(
            to_email=meeting.owner.email,
            subject=content.subject,
            html=content.html,
        )
    except Exception:
        logger.exception("notification failed for meeting {}", meeting.id)
