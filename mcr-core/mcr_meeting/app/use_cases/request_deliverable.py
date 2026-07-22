from pydantic import UUID4

from mcr_meeting.app.db.deliverable_repository import (
    get_active_by_meeting_and_type,
    save_deliverable,
    soft_delete_by_id,
)
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableConcurrentlyCreatedException,
    MeetingStateConflictException,
    NotFoundException,
    TaskCreationException,
)
from mcr_meeting.app.infrastructure.s3 import get_transcription_object_name
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.use_cases._shared.report_dispatch import (
    dispatch_report_generation,
)


def request_deliverable(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    deliverable_type: DeliverableType,
    custom_prompt: str | None = None,
) -> Deliverable:
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    try:
        existing_deliverable = get_active_by_meeting_and_type(
            meeting_id=meeting.id, deliverable_type=deliverable_type
        )
        if _is_already_pending(existing_deliverable):
            return existing_deliverable
        soft_delete_by_id(deliverable_id=existing_deliverable.id)
    except NotFoundException:
        pass

    try:
        return _persist_and_dispatch(
            meeting=meeting,
            deliverable_type=deliverable_type,
            custom_prompt=custom_prompt,
        )
    except DeliverableConcurrentlyCreatedException as concurrent_exc:
        try:
            return get_active_by_meeting_and_type(
                meeting_id=meeting.id, deliverable_type=deliverable_type
            )
        except NotFoundException:
            raise concurrent_exc from None


def _is_already_pending(deliverable: Deliverable) -> bool:
    return deliverable.status == DeliverableStatus.PENDING


def _persist_and_dispatch(
    meeting: Meeting,
    deliverable_type: DeliverableType,
    custom_prompt: str | None,
) -> Deliverable:
    try:
        with UnitOfWork():
            deliverable = save_deliverable(
                Deliverable(
                    meeting_id=meeting.id,
                    type=deliverable_type,
                    status=DeliverableStatus.PENDING,
                )
            )

            transcription_object_name = _resolve_transcription_object_name(meeting)
            dispatch_report_generation(
                meeting, deliverable, transcription_object_name, custom_prompt
            )
            return deliverable
    except (
        DeliverableConcurrentlyCreatedException,
        MeetingStateConflictException,
        TaskCreationException,
        ValueError,
    ):
        raise
    except Exception as exc:
        raise TaskCreationException(str(exc)) from exc


def _resolve_transcription_object_name(meeting: Meeting) -> str:
    if meeting.transcription_filename is None:
        raise NotFoundException(
            f"Could not find meeting transcription: id={meeting.id}"
        )
    return get_transcription_object_name(
        meeting_id=meeting.id, filename=meeting.transcription_filename
    )
