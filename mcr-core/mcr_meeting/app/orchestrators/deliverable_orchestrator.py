from collections.abc import Callable
from io import BytesIO
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError

from mcr_meeting.app.exceptions.exceptions import BadRequestException
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.orchestrators.meeting_orchestrator import get_meeting
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    complete_report,
    fail_report,
    reset_report,
    start_report,
)
from mcr_meeting.app.schemas.report_generation import ReportResponse, ReportType
from mcr_meeting.app.services.deliverable_service import (
    create_pending_deliverable,
    find_active_deliverable,
    get_deliverable,
    mark_deliverable_available,
    mark_deliverable_failed,
    soft_delete_deliverable_row,
)
from mcr_meeting.app.services.deliverable_service import (
    list_deliverables_for_meeting as _service_list_for_meeting,
)
from mcr_meeting.app.services.meeting_service import get_meeting_service
from mcr_meeting.app.services.report_task_service import (
    get_formatted_report_from_s3,
    get_typed_deliverable_from_s3,
)
from mcr_meeting.app.services.transcription_task_service import (
    get_formatted_transcription_from_s3,
)

_REPORT_TYPE_BY_DELIVERABLE = {
    DeliverableType.DECISION_RECORD: ReportType.DECISION_RECORD,
    DeliverableType.DETAILED_SYNTHESIS: ReportType.DETAILED_SYNTHESIS,
}


class DeliverableFileResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    buffer: BytesIO
    meeting_name: str


def _refresh_meeting_status(meeting_id: int) -> MeetingStatus:
    return get_meeting_service(meeting_id=meeting_id).status  # type: ignore[return-value]


def _apply_idempotent_sm_call(  # type: ignore[explicit-any]
    sm_call: Callable[..., Any],
    meeting_id: int,
    expected_target_status: MeetingStatus,
    **kwargs: Any,
) -> None:
    """Run an SM transition; swallow the error if the meeting already
    landed on the expected target state (concurrent same-direction call)."""
    try:
        sm_call(meeting_id=meeting_id, **kwargs)
    except ValueError:
        if _refresh_meeting_status(meeting_id) != expected_target_status:
            raise


def _create_pending_with_race_recovery(
    meeting_id: int, deliverable_type: DeliverableType
) -> Deliverable:
    """Create a PENDING deliverable; on partial-unique-index conflict from a
    concurrent request, recover by returning the surviving active row."""
    try:
        return create_pending_deliverable(
            meeting_id=meeting_id, deliverable_type=deliverable_type
        )
    except IntegrityError:
        existing = find_active_deliverable(
            meeting_id=meeting_id, deliverable_type=deliverable_type
        )
        if existing is None:
            raise
        return existing


def request_deliverable(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    deliverable_type: DeliverableType,
) -> Deliverable:
    if deliverable_type == DeliverableType.TRANSCRIPTION:
        raise BadRequestException(
            "TRANSCRIPTION deliverables are produced by the capture pipeline "
            "and cannot be requested through this endpoint."
        )

    report_type = _REPORT_TYPE_BY_DELIVERABLE[deliverable_type]

    meeting = get_meeting(meeting_id=meeting_id, user_keycloak_uuid=user_keycloak_uuid)

    existing = find_active_deliverable(
        meeting_id=meeting.id, deliverable_type=deliverable_type
    )
    if existing is not None and existing.status == DeliverableStatus.PENDING:
        return existing

    if existing is not None:
        # Soft-delete (not hard) so the partial unique index — which excludes
        # DELETED rows — admits the next INSERT.
        soft_delete_deliverable_row(deliverable_id=existing.id)

    deliverable = _create_pending_with_race_recovery(
        meeting_id=meeting.id, deliverable_type=deliverable_type
    )
    if deliverable.status != DeliverableStatus.PENDING:
        return deliverable

    if meeting.status in (MeetingStatus.REPORT_DONE, MeetingStatus.REPORT_FAILED):
        _apply_idempotent_sm_call(
            reset_report,
            meeting_id=meeting.id,
            expected_target_status=MeetingStatus.TRANSCRIPTION_DONE,
            user_keycloak_uuid=user_keycloak_uuid,
        )

    _apply_idempotent_sm_call(
        start_report,
        meeting_id=meeting.id,
        expected_target_status=MeetingStatus.REPORT_PENDING,
        user_keycloak_uuid=user_keycloak_uuid,
        report_type=report_type,
        deliverable_id=deliverable.id,
    )

    return deliverable


def mark_deliverable_success(
    deliverable_id: int,
    external_url: str | None,
    report_response: ReportResponse,
) -> Deliverable:
    deliverable = mark_deliverable_available(
        deliverable_id=deliverable_id, external_url=external_url
    )
    _apply_idempotent_sm_call(
        complete_report,
        meeting_id=deliverable.meeting_id,
        expected_target_status=MeetingStatus.REPORT_DONE,
        report_response=report_response,
    )
    return deliverable


def mark_deliverable_failure(deliverable_id: int) -> Deliverable:
    deliverable = mark_deliverable_failed(deliverable_id=deliverable_id)
    _apply_idempotent_sm_call(
        fail_report,
        meeting_id=deliverable.meeting_id,
        expected_target_status=MeetingStatus.REPORT_FAILED,
    )
    return deliverable


def soft_delete_deliverable(deliverable_id: int, user_keycloak_uuid: UUID4) -> None:
    deliverable = get_deliverable(deliverable_id=deliverable_id)
    get_meeting(
        meeting_id=deliverable.meeting_id, user_keycloak_uuid=user_keycloak_uuid
    )
    soft_delete_deliverable_row(deliverable_id=deliverable_id)
    _apply_idempotent_sm_call(
        reset_report,
        meeting_id=deliverable.meeting_id,
        expected_target_status=MeetingStatus.TRANSCRIPTION_DONE,
        user_keycloak_uuid=user_keycloak_uuid,
    )


def list_deliverables_for_meeting(
    meeting_id: int, user_keycloak_uuid: UUID4
) -> list[Deliverable]:
    get_meeting(meeting_id=meeting_id, user_keycloak_uuid=user_keycloak_uuid)
    return _service_list_for_meeting(meeting_id=meeting_id)


def get_deliverable_file(
    deliverable_id: int, user_keycloak_uuid: UUID4
) -> DeliverableFileResult:
    deliverable = get_deliverable(deliverable_id=deliverable_id)
    if deliverable.status != DeliverableStatus.AVAILABLE:
        raise BadRequestException(
            f"Deliverable is not downloadable: id={deliverable_id}, status={deliverable.status.value}"
        )
    meeting = get_meeting(
        meeting_id=deliverable.meeting_id, user_keycloak_uuid=user_keycloak_uuid
    )
    buffer: BytesIO
    if deliverable.type == DeliverableType.TRANSCRIPTION:
        buffer = get_formatted_transcription_from_s3(meeting)
    else:
        typed = get_typed_deliverable_from_s3(
            meeting=meeting, deliverable_type=deliverable.type
        )
        buffer = typed if typed is not None else get_formatted_report_from_s3(meeting)
    return DeliverableFileResult(buffer=buffer, meeting_name=meeting.name or "")
