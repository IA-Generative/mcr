from pydantic import UUID4

from mcr_meeting.app.db import deliverable_repository, meeting_repository
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.models.deliverable_model import Deliverable


def list_deliverables_for_meeting(
    meeting_id: int, user_keycloak_uuid: UUID4
) -> list[Deliverable]:
    meeting = meeting_repository.get_meeting_by_id(meeting_id)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    return deliverable_repository.list_by_meeting(meeting_id=meeting_id)
