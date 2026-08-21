from pydantic import UUID4

from mcr_meeting.app.db import deliverable_feedback_repository, deliverable_repository
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_owner


def deactivate_deliverable_feedback(
    deliverable_id: int, user_keycloak_uuid: UUID4
) -> None:
    _, owner_keycloak_uuid = deliverable_repository.get_by_id_with_owner_uuid(
        deliverable_id
    )
    authorize_meeting_owner(owner_keycloak_uuid, user_keycloak_uuid)

    with UnitOfWork():
        deliverable_feedback_repository.deactivate(deliverable_id=deliverable_id)
