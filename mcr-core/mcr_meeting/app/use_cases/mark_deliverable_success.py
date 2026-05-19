from loguru import logger

from mcr_meeting.app.db import deliverable_repository, meeting_repository
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain import deliverable_transitions
from mcr_meeting.app.domain.report_rendering import render_report
from mcr_meeting.app.infrastructure.email import notify_report_ready
from mcr_meeting.app.infrastructure.s3 import upload_report_to_s3
from mcr_meeting.app.models.deliverable_model import Deliverable
from mcr_meeting.app.models.meeting_model import Meeting, MeetingStatus
from mcr_meeting.app.schemas.report_generation import ReportResponse
from mcr_meeting.app.services.meeting_transition_record_service import (
    create_transition_record_service,
)


def mark_deliverable_success(
    deliverable_id: int,
    external_url: str | None,
    report_response: ReportResponse,
) -> Deliverable:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    meeting = meeting_repository.get_meeting_by_id(deliverable.meeting_id)

    docx = render_report(report_response, meeting_name=meeting.name or "")
    upload_report_to_s3(meeting.id, deliverable.type, docx)
    _persist_success_atomically(deliverable, meeting, external_url)

    create_transition_record_service(meeting.id, MeetingStatus.REPORT_DONE)
    _notify_report_ready_best_effort(meeting.id)
    return deliverable


def _persist_success_atomically(
    deliverable: Deliverable, meeting: Meeting, external_url: str | None
) -> None:
    with UnitOfWork():
        deliverable_transitions.mark_available(deliverable, external_url=external_url)
        deliverable_repository.save_deliverable(deliverable)

        meeting.status = MeetingStatus.REPORT_DONE
        meeting_repository.update_meeting(meeting)


def _notify_report_ready_best_effort(meeting_id: int) -> None:
    try:
        notify_report_ready(meeting_id=meeting_id)
    except Exception:
        logger.exception("notification failed for meeting {}", meeting_id)
