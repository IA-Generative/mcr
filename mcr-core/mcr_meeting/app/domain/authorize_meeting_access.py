from pydantic import UUID4

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.meeting_model import Meeting
from mcr_meeting.app.schemas.caller_schema import Caller


def authorize_meeting_access(
    meeting: Meeting, current_user_keycloak_uuid: UUID4
) -> None:
    if (
        current_user_keycloak_uuid is not None
        and meeting.owner.keycloak_uuid != current_user_keycloak_uuid
    ):
        raise ForbiddenAccessException("Meeting is owned by a different user")


def authorize_meeting_owner_or_admin(meeting_owner_id: int, caller: Caller) -> None:
    if _is_owner(meeting_owner_id, caller) or caller.is_admin:
        return
    raise ForbiddenAccessException("Not owner and not admin")


def _is_owner(meeting_owner_id: int, caller: Caller) -> bool:
    return meeting_owner_id == caller.user_id
