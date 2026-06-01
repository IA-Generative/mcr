from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.infrastructure.s3 import stream_meeting_audio

MAX_DELAY_TO_GET_AUDIO = 7  # In days


@dataclass
class MeetingAudioStream:
    iterator: Iterator[bytes]
    media_type: str


def get_meeting_audio(meeting_id: int, user_keycloak_uuid: UUID4) -> MeetingAudioStream:
    meeting = get_meeting_by_id(meeting_id)
    authorize_meeting_access(meeting, user_keycloak_uuid)

    if _is_audio_expired(meeting.creation_date):
        raise ForbiddenAccessException(
            f"Meeting must have been created in the last {MAX_DELAY_TO_GET_AUDIO} days to access its audio"
        )

    iterator, media_type = stream_meeting_audio(meeting_id)
    return MeetingAudioStream(iterator=iterator, media_type=media_type)


def _is_audio_expired(creation_date: datetime | None) -> bool:
    if creation_date is None:
        return False

    return (
        datetime.now(timezone.utc) - creation_date.replace(tzinfo=timezone.utc)
    ).days >= MAX_DELAY_TO_GET_AUDIO
