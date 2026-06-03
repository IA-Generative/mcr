from datetime import datetime, timezone

from pydantic import UUID4

from mcr_meeting.app.db.deliverable_repository import (
    find_active_by_meeting_and_type,
    save_deliverable,
    soft_delete_by_id,
)
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id, update_meeting
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.domain.meeting_transitions import reset_and_start_report
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableConcurrentlyCreatedException,
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
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.celery_types import MCRReportGenerationTasks
from mcr_meeting.app.schemas.report_generation import ReportType

_REPORT_TYPE_BY_DELIVERABLE = {
    DeliverableType.DECISION_RECORD: ReportType.DECISION_RECORD,
    DeliverableType.DETAILED_SYNTHESIS: ReportType.DETAILED_SYNTHESIS,
    DeliverableType.CUSTOM_REPORT: ReportType.CUSTOM_REPORT,
    DeliverableType.NARRATIVE_SYNTHESIS: ReportType.NARRATIVE_SYNTHESIS,
}


def request_deliverable(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    deliverable_type: DeliverableType,
    custom_prompt: str | None = None,
) -> Deliverable:
    report_type = _REPORT_TYPE_BY_DELIVERABLE[deliverable_type]

    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    existing_deliverable = find_active_by_meeting_and_type(
        meeting_id=meeting.id, deliverable_type=deliverable_type
    )

    if existing_deliverable is not None:
        if _is_already_pending(existing_deliverable):
            return existing_deliverable
        soft_delete_by_id(deliverable_id=existing_deliverable.id)

    try:
        return _persist_and_dispatch(
            meeting=meeting,
            deliverable_type=deliverable_type,
            report_type=report_type,
            custom_prompt=custom_prompt,
        )
    except DeliverableConcurrentlyCreatedException:
        winner = find_active_by_meeting_and_type(
            meeting_id=meeting.id, deliverable_type=deliverable_type
        )
        if winner is None:
            raise
        return winner


def _is_already_pending(deliverable: Deliverable) -> bool:
    return deliverable.status == DeliverableStatus.PENDING


def _persist_and_dispatch(
    meeting: Meeting,
    deliverable_type: DeliverableType,
    report_type: ReportType,
    custom_prompt: str | None,
) -> Deliverable:
    try:
        with UnitOfWork():
            reset_and_start_report(meeting)
            update_meeting(meeting)
            deliverable = save_deliverable(
                Deliverable(
                    meeting_id=meeting.id,
                    type=deliverable_type,
                    status=DeliverableStatus.PENDING,
                )
            )

            save_meeting_transition_record(
                _build_transition_record(meeting.id, meeting.status)
            )

            transcription_object_name = _resolve_transcription_object_name(meeting)
            kwargs = _build_report_task_kwargs(meeting, deliverable, custom_prompt)
            celery_producer_app.send_task(
                MCRReportGenerationTasks.REPORT,
                args=[meeting.id, transcription_object_name, report_type],
                kwargs=kwargs,
            )
            return deliverable
    except (DeliverableConcurrentlyCreatedException, ValueError):
        raise
    except Exception as exc:
        raise TaskCreationException(str(exc)) from exc


def _build_transition_record(
    meeting_id: int, next_status: MeetingStatus
) -> MeetingTransitionRecord:
    return MeetingTransitionRecord(
        meeting_id=meeting_id,
        timestamp=datetime.now(timezone.utc),
        status=next_status,
    )


def _resolve_transcription_object_name(meeting: Meeting) -> str:
    if meeting.transcription_filename is None:
        raise NotFoundException(
            f"Could not find meeting transcription: id={meeting.id}"
        )
    return get_transcription_object_name(
        meeting_id=meeting.id, filename=meeting.transcription_filename
    )


def _build_report_task_kwargs(
    meeting: Meeting,
    deliverable: Deliverable,
    custom_prompt: str | None,
) -> dict[str, str | int]:
    kwargs: dict[str, str | int] = {
        "owner_keycloak_uuid": str(meeting.owner.keycloak_uuid),
        "deliverable_id": deliverable.id,
    }
    if custom_prompt is not None:
        kwargs["custom_prompt"] = custom_prompt
    if meeting.notes is not None:
        kwargs["notes_content"] = meeting.notes
    return kwargs
