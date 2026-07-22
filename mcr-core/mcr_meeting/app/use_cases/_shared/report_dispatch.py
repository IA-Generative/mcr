from mcr_meeting.app.infrastructure.celery import enqueue_report_generation_task
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableType
from mcr_meeting.app.schemas.report_generation import ReportType

_REPORT_TYPE_BY_DELIVERABLE = {
    DeliverableType.DECISION_RECORD: ReportType.DECISION_RECORD,
    DeliverableType.DETAILED_SYNTHESIS: ReportType.DETAILED_SYNTHESIS,
    DeliverableType.CUSTOM_REPORT: ReportType.CUSTOM_REPORT,
}


def dispatch_report_generation(
    meeting: Meeting,
    deliverable: Deliverable,
    transcription_object_name: str,
    custom_prompt: str | None = None,
) -> None:
    enqueue_report_generation_task(
        meeting_id=meeting.id,
        transcription_object_name=transcription_object_name,
        report_type=_REPORT_TYPE_BY_DELIVERABLE[deliverable.type],
        kwargs=_build_report_task_kwargs(meeting, deliverable, custom_prompt),
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
