from uuid import UUID

from mcr_meeting.app.models import Meeting
from mcr_meeting.app.services.meeting_service import (
    get_meeting_service,
)


def get_meeting(
    meeting_id: int,
    user_keycloak_uuid: UUID,
) -> Meeting:
    return get_meeting_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )
