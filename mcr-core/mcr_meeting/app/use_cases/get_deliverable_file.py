from io import BytesIO

from pydantic import UUID4

from mcr_meeting.app.db import deliverable_repository, meeting_repository
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    NotFoundException,
)
from mcr_meeting.app.infrastructure.s3 import (
    get_report_from_s3,
    get_transcription_from_s3,
    get_typed_deliverable_from_s3,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableStatus, DeliverableType
from mcr_meeting.app.schemas.deliverable_schema import DeliverableFileResult


def get_deliverable_file(
    deliverable_id: int, user_keycloak_uuid: UUID4
) -> DeliverableFileResult:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    if deliverable.status != DeliverableStatus.AVAILABLE:
        raise BadRequestException(
            f"Deliverable is not downloadable: id={deliverable_id}, "
            f"status={deliverable.status.value}"
        )

    meeting = meeting_repository.get_meeting_by_id(deliverable.meeting_id)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    buffer = _resolve_buffer(meeting, deliverable.type)
    return DeliverableFileResult(
        buffer=buffer,
        meeting_name=meeting.name or "",
        deliverable_type=deliverable.type,
    )


def _resolve_buffer(meeting: Meeting, deliverable_type: DeliverableType) -> BytesIO:
    if deliverable_type == DeliverableType.TRANSCRIPTION:
        return _transcription_buffer(meeting)

    typed = get_typed_deliverable_from_s3(meeting.id, deliverable_type)
    if typed is not None:
        return typed
    return _report_buffer(meeting)


def _transcription_buffer(meeting: Meeting) -> BytesIO:
    if meeting.transcription_filename is None:
        raise NotFoundException(
            "Couldn't get transcription as meeting.transcription_filename is empty"
        )
    return get_transcription_from_s3(meeting.id, meeting.transcription_filename)


def _report_buffer(meeting: Meeting) -> BytesIO:
    if meeting.report_filename is None:
        raise NotFoundException(
            "Couldn't get report as meeting.report_filename is empty"
        )
    return get_report_from_s3(meeting.id, meeting.report_filename)
