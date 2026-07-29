from pydantic import UUID4

from mcr_meeting.app.db import deliverable_feedback_repository, deliverable_repository
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access


def deactivate_deliverable_feedback(
    deliverable_id: int, user_keycloak_uuid: UUID4
) -> None:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    authorize_meeting_access(
        get_meeting_by_id(deliverable.meeting_id), user_keycloak_uuid
    )

    with UnitOfWork():
        deliverable_feedback_repository.deactivate(deliverable_id=deliverable_id)
