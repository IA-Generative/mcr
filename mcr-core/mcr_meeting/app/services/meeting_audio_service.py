from collections.abc import Generator, Iterator
from datetime import datetime, timezone

from fastapi.responses import StreamingResponse
from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.s3_service import (
    get_file_from_s3,
    get_objects_list_from_prefix,
    validate_object_list,
)

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

    s3_chunk_iterator = get_objects_list_from_prefix(prefix=f"{meeting_id}/")
    validated_iterator = validate_object_list(s3_chunk_iterator)

    return StreamingResponse(
        stream_audio_chunks(validated_iterator), media_type="audio/webm"
    )


def stream_audio_chunks(
    obj_iterator: Iterator[S3Object],
) -> Generator[bytes, None, None]:
    for obj_info in obj_iterator:
        audio_chunk_data = get_file_from_s3(object_name=obj_info.object_name)
        yield audio_chunk_data.read()


def isAudioExpired(creation_date: datetime | None) -> bool:
    if creation_date is None:
        return False

    return (
        datetime.now(timezone.utc) - creation_date.replace(tzinfo=timezone.utc)
    ).days >= MAX_DELAY_TO_GET_AUDIO
