from datetime import datetime, timezone

from loguru import logger

from mcr_meeting.app.db import deliverable_repository, meeting_repository
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain import deliverable_transitions, meeting_transitions
from mcr_meeting.app.domain.email import build_report_ready_email
from mcr_meeting.app.domain.report_rendering import render_report
from mcr_meeting.app.exceptions.exceptions import DeliverableStateConflictException
from mcr_meeting.app.infrastructure import email as email_infra
from mcr_meeting.app.infrastructure.s3 import upload_report_to_s3
from mcr_meeting.app.models.deliverable_model import Deliverable
from mcr_meeting.app.models.meeting_model import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.report_generation import ReportResponse


def mark_deliverable_success(
    deliverable_id: int,
    external_url: str | None,
    report_response: ReportResponse,
) -> Deliverable:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    meeting = meeting_repository.get_meeting_with_owner(deliverable.meeting_id)

    try:
        docx = render_report(report_response, meeting_name=meeting.name or "")
        upload_report_to_s3(meeting.id, deliverable.type, docx)

        deliverable_transitions.mark_available(deliverable, external_url=external_url)
        meeting_transitions.complete_report(meeting)
        _persist_success_atomically(deliverable, meeting)
    except DeliverableStateConflictException:
        raise
    except Exception:
        _mark_failed_best_effort(deliverable)
        raise

    _notify_report_ready_best_effort(meeting)
    return deliverable


def _persist_success_atomically(deliverable: Deliverable, meeting: Meeting) -> None:
    with UnitOfWork():
        deliverable_repository.save_deliverable(deliverable)
        meeting_repository.update_meeting(meeting)

        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=meeting.status,
            )
        )


def _mark_failed_best_effort(deliverable: Deliverable) -> None:
    try:
        with UnitOfWork():
            deliverable_transitions.mark_failed(deliverable)
            deliverable_repository.save_deliverable(deliverable)
    except Exception:
        logger.exception("could not mark deliverable {} as FAILED", deliverable.id)


def _notify_report_ready_best_effort(meeting: Meeting) -> None:
    try:
        content = build_report_ready_email(meeting.name or "", meeting.id)
        email_infra.send_email(
            to_email=meeting.owner.email,
            subject=content.subject,
            html=content.html,
        )
    except Exception:
        logger.exception("notification failed for meeting {}", meeting.id)
