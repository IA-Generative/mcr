from mcr_meeting.app.db import deliverable_repository
from mcr_meeting.app.domain import deliverable_transitions
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.infrastructure.celery import enqueue_report_generation_task
from mcr_meeting.app.infrastructure.s3 import get_transcription_object_name
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableType
from mcr_meeting.app.schemas.report_generation import ReportType

_REPORT_TYPE_BY_DELIVERABLE = {
    DeliverableType.DECISION_RECORD: ReportType.DECISION_RECORD,
    DeliverableType.DETAILED_SYNTHESIS: ReportType.DETAILED_SYNTHESIS,
    DeliverableType.CUSTOM_REPORT: ReportType.CUSTOM_REPORT,
}


def dispatch_requested_report(
    meeting: Meeting,
    deliverable: Deliverable,
    custom_prompt: str | None = None,
) -> Deliverable:
    deliverable_transitions.dispatch(deliverable)
    deliverable_repository.save_deliverable(deliverable)
    enqueue_report_generation_task(
        meeting_id=meeting.id,
        transcription_object_name=_resolve_transcription_object_name(meeting),
        report_type=_REPORT_TYPE_BY_DELIVERABLE[deliverable.type],
        kwargs=_build_report_task_kwargs(meeting, deliverable, custom_prompt),
    )
    return deliverable


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
    custom_prompt: str | None = None,
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
