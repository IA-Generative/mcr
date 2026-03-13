from datetime import datetime, timezone

from fastapi.responses import StreamingResponse
from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException

MAX_DELAY_TO_GET_AUDIO = 7  # In days


def get_meeting_audio_service(
    meeting_id: int, current_user_keycloak_uuid: UUID4 | None = None
) -> StreamingResponse:
    meeting = get_meeting_by_id(meeting_id)

    if (
        current_user_keycloak_uuid is not None
        and meeting.owner.keycloak_uuid != current_user_keycloak_uuid
    ):
        raise ForbiddenAccessException("Meeting is owned by a different user")

    if isAudioExpired(meeting.creation_date):
        raise ForbiddenAccessException(
            f"Meeting must have been created in the last {MAX_DELAY_TO_GET_AUDIO} days to access its audio"
        )

    return StreamingResponse(content="")


def isAudioExpired(creation_date: datetime | None) -> bool:
    if creation_date is None:
        return False

    return (
        datetime.now(timezone.utc) - creation_date.replace(tzinfo=timezone.utc)
    ).days >= MAX_DELAY_TO_GET_AUDIO
