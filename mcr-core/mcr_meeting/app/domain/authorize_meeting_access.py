from pydantic import UUID4

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.meeting_model import Meeting


def authorize_meeting_access(
    meeting: Meeting, current_user_keycloak_uuid: UUID4
) -> None:
    if (
        current_user_keycloak_uuid is not None
        and meeting.owner.keycloak_uuid != current_user_keycloak_uuid
    ):
        raise ForbiddenAccessException("Meeting is owned by a different user")
