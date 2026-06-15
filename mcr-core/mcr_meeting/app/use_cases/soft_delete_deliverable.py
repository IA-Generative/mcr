from pydantic import UUID4

from mcr_meeting.app.db import deliverable_repository, meeting_repository
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain import deliverable_transitions
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access


def soft_delete_deliverable(deliverable_id: int, user_keycloak_uuid: UUID4) -> None:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    meeting = meeting_repository.get_meeting_by_id(deliverable.meeting_id)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    with UnitOfWork():
        deliverable_transitions.soft_delete(deliverable)
        deliverable_repository.save_deliverable(deliverable)
