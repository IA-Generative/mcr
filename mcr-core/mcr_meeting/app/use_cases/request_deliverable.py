from datetime import datetime, timezone

from loguru import logger
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError

from mcr_meeting.app.db.deliverable_repository import (
    find_active_by_meeting_and_type,
    save_deliverable,
    soft_delete_by_id,
)
from mcr_meeting.app.db.deliverable_repository import (
    set_status as set_deliverable_status,
)
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meetings.meeting_validator import (
    validate_meeting_ownership,
)
from mcr_meeting.app.domain.state_machine.transition_validator import (
    validate_transition,
)
from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
    TaskCreationException,
)
from mcr_meeting.app.infrastructure.celery import celery_producer_app
from mcr_meeting.app.infrastructure.s3 import get_transcription_object_name
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import MeetingEvent, MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.celery_types import MCRReportGenerationTasks
from mcr_meeting.app.schemas.report_generation import ReportType

_REPORT_TYPE_BY_DELIVERABLE = {
    DeliverableType.DECISION_RECORD: ReportType.DECISION_RECORD,
    DeliverableType.DETAILED_SYNTHESIS: ReportType.DETAILED_SYNTHESIS,
    DeliverableType.CUSTOM_REPORT: ReportType.CUSTOM_REPORT,
}


def request_deliverable(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    deliverable_type: DeliverableType,
    custom_prompt: str | None = None,
) -> Deliverable:
    """Request a deliverable generation.

    Orchestrates the full happy path without going through ``sm.send()`` so
    that the state-machine ``after_*`` handlers are not triggered. The use
    case itself owns side effects (status update, transition record, Celery
    dispatch) and rolls them back if Celery dispatch fails.
    """
    report_type = _REPORT_TYPE_BY_DELIVERABLE[deliverable_type]

    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    validate_meeting_ownership(meeting, user_keycloak_uuid)

    existing = find_active_by_meeting_and_type(
        meeting_id=meeting.id, deliverable_type=deliverable_type
    )
    if existing is not None and existing.status == DeliverableStatus.PENDING:
        return existing
    if existing is not None:
        # Soft delete (not hard) so the partial unique index — which excludes
        # DELETED rows — admits the next INSERT.
        soft_delete_by_id(deliverable_id=existing.id)

    if meeting.status in (MeetingStatus.REPORT_DONE, MeetingStatus.REPORT_FAILED):
        transcription_done_status = validate_transition(
            meeting, MeetingEvent.RESET_REPORT
        )
        # Apply in memory so the next validate_transition sees the post-reset
        # state. Both transitions are persisted atomically in _persist_request.
        meeting.status = transcription_done_status

    if meeting.transcription_filename is None:
        raise NotFoundException(
            f"Could not find meeting transcription: id={meeting.id}"
        )

    report_pending_status = validate_transition(meeting, MeetingEvent.START_REPORT)

    transcription_object_name = get_transcription_object_name(
        meeting_id=meeting.id, filename=meeting.transcription_filename
    )
    transition_record = _create_transition_record(
        meeting_id=meeting.id, next_status=report_pending_status
    )
    deliverable = _persist_deliverable_meeting_status_and_transition_record(
        meeting=meeting,
        deliverable_type=deliverable_type,
        transition_record=transition_record,
    )

    _dispatch_celery_task_or_compensate(
        meeting=meeting,
        deliverable=deliverable,
        report_type=report_type,
        transcription_object_name=transcription_object_name,
        custom_prompt=custom_prompt,
    )

    return deliverable


def _create_transition_record(
    meeting_id: int,
    next_status: MeetingStatus,
) -> MeetingTransitionRecord | None:
    status_with_special_transition_record_handlers = [
        MeetingStatus.TRANSCRIPTION_PENDING,
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
    ]

    if next_status in status_with_special_transition_record_handlers:
        return None

    current_time = datetime.now(timezone.utc)

    transition_record = MeetingTransitionRecord(
        meeting_id=meeting_id,
        timestamp=current_time,
        status=next_status,
    )
    return transition_record


def _update_meeting_status(meeting: Meeting, meeting_status: MeetingStatus) -> None:
    meeting.status = meeting_status
    update_meeting(meeting)


def _persist_deliverable_meeting_status_and_transition_record(
    meeting: Meeting,
    deliverable_type: DeliverableType,
    transition_record: MeetingTransitionRecord | None,
) -> Deliverable:
    """Persist the deliverable + meeting status + transition record atomically.

    Recovers from a concurrent-request ``IntegrityError`` on the partial unique
    index by reloading the surviving active deliverable.
    """
    try:
        with UnitOfWork():
            deliverable = save_deliverable(
                Deliverable(
                    meeting_id=meeting.id,
                    type=deliverable_type,
                    status=DeliverableStatus.PENDING,
                )
            )
            _update_meeting_status(meeting, MeetingStatus.REPORT_PENDING)
            if transition_record is not None:
                save_meeting_transition_record(transition_record)
            return deliverable
    except IntegrityError:
        existing = find_active_by_meeting_and_type(
            meeting_id=meeting.id, deliverable_type=deliverable_type
        )
        if existing is None:
            raise
        return existing


def _dispatch_celery_task_or_compensate(
    meeting: Meeting,
    deliverable: Deliverable,
    report_type: ReportType,
    transcription_object_name: str,
    custom_prompt: str | None,
) -> None:
    """Send the Celery task. On failure, mark the deliverable FAILED and the
    meeting REPORT_FAILED so a retry from the user produces a fresh cycle."""
    task_kwargs: dict[str, str | int] = {
        "owner_keycloak_uuid": str(meeting.owner.keycloak_uuid),
        "deliverable_id": deliverable.id,
    }
    if custom_prompt is not None:
        task_kwargs["custom_prompt"] = custom_prompt

    try:
        celery_producer_app.send_task(
            MCRReportGenerationTasks.REPORT,
            args=[meeting.id, transcription_object_name, report_type],
            kwargs=task_kwargs,
        )
        logger.info("Report generation task created for meeting: {}", meeting.id)
    except Exception as exc:
        logger.exception(
            "Celery dispatch failed; reverting deliverable {} for meeting {}",
            deliverable.id,
            meeting.id,
        )
        _compensate_failed_dispatch(meeting=meeting, deliverable=deliverable)
        raise TaskCreationException(str(exc))


def _compensate_failed_dispatch(meeting: Meeting, deliverable: Deliverable) -> None:
    """Best-effort revert when Celery dispatch fails after DB commit.

    Falling back to ``FAIL_REPORT`` (rather than ``RESET_REPORT``) keeps the
    incident visible in the UI and lets the user trigger a fresh attempt: the
    next ``request_deliverable_use_case`` call will soft-delete the FAILED row
    and create a new cycle.
    """
    try:
        report_failed_status = validate_transition(meeting, MeetingEvent.FAIL_REPORT)
        transition_record = _create_transition_record(
            meeting_id=meeting.id, next_status=report_failed_status
        )
        with UnitOfWork():
            set_deliverable_status(
                deliverable_id=deliverable.id, status=DeliverableStatus.FAILED
            )
            _update_meeting_status(meeting, MeetingStatus.REPORT_FAILED)
            if transition_record is not None:
                save_meeting_transition_record(transition_record)
    except Exception:
        logger.exception(
            "Compensation failed for deliverable {} (meeting {})",
            deliverable.id,
            meeting.id,
        )
