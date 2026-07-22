from pydantic import UUID4

from mcr_meeting.app.db.deliverable_repository import (
    get_active_by_meeting_and_type,
    save_deliverable,
    soft_delete_by_id,
)
from mcr_meeting.app.db.meeting_repository import get_meeting_for_update
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableConcurrentlyCreatedException,
    NotFoundException,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.use_cases._shared.report_dispatch import (
    dispatch_requested_report,
)


def request_deliverable(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    deliverable_type: DeliverableType,
    custom_prompt: str | None = None,
) -> Deliverable:
    try:
        return _decide_and_persist(
            meeting_id=meeting_id,
            user_keycloak_uuid=user_keycloak_uuid,
            deliverable_type=deliverable_type,
            custom_prompt=custom_prompt,
        )
    except DeliverableConcurrentlyCreatedException as concurrent_exc:
        try:
            return get_active_by_meeting_and_type(
                meeting_id=meeting_id, deliverable_type=deliverable_type
            )
        except NotFoundException:
            raise concurrent_exc from None


def _decide_and_persist(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    deliverable_type: DeliverableType,
    custom_prompt: str | None,
) -> Deliverable:
    with UnitOfWork():
        meeting = get_meeting_for_update(
            meeting_id, with_deliverables=True, with_owner=True
        )
        authorize_meeting_access(meeting, user_keycloak_uuid)

        try:
            existing = get_active_by_meeting_and_type(
                meeting_id=meeting.id, deliverable_type=deliverable_type
            )
            if _is_in_flight(existing):
                return existing
            soft_delete_by_id(deliverable_id=existing.id)
        except NotFoundException:
            pass

        deliverable = save_deliverable(
            Deliverable(
                meeting_id=meeting.id,
                type=deliverable_type,
                status=DeliverableStatus.REQUESTED,
            )
        )

        if _is_transcription_available(meeting):
            dispatch_requested_report(meeting, deliverable, custom_prompt)
        return deliverable


def _is_in_flight(deliverable: Deliverable) -> bool:
    return deliverable.status in (
        DeliverableStatus.REQUESTED,
        DeliverableStatus.PENDING,
    )


def _is_transcription_available(meeting: Meeting) -> bool:
    return any(
        deliverable.type == DeliverableType.TRANSCRIPTION
        and deliverable.status == DeliverableStatus.AVAILABLE
        for deliverable in meeting.deliverables
    )
