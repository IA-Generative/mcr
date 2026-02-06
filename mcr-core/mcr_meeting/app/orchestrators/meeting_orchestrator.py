from typing import List
from uuid import UUID

from mcr_meeting.app.models import Meeting
from mcr_meeting.app.schemas.meeting_schema import (
    MeetingCreate,
    MeetingResponse,
    MeetingUpdate,
    MeetingWithPresignedUrl,
)
from mcr_meeting.app.schemas.S3_types import (
    PresignedAudioFileRequest,
)
from mcr_meeting.app.services.audio_upload_service import (
    get_presigned_upload_url,
)
from mcr_meeting.app.services.meeting_service import (
    create_meeting_service,
    get_meeting_service,
    get_meetings_service,
    update_meeting_service,
)


async def create_meeting_with_presigned_url(
    meeting_data: MeetingCreate,
    presigned_request: PresignedAudioFileRequest,
    user_keycloak_uuid: UUID,
) -> MeetingWithPresignedUrl:
    meeting = create_meeting_service(
        meeting_data=meeting_data,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    presigned_url = await get_presigned_upload_url(
        meeting_id=meeting.id,
        presigned_request=presigned_request,
    )

    return MeetingWithPresignedUrl(
        meeting=MeetingResponse.model_validate(meeting),
        presigned_url=presigned_url,
    )


def create_meeting(
    meeting_data: MeetingCreate,
    user_keycloak_uuid: UUID,
) -> Meeting:
    return create_meeting_service(
        meeting_data=meeting_data,
        user_keycloak_uuid=user_keycloak_uuid,
    )


def get_meeting(
    meeting_id: int,
    user_keycloak_uuid: UUID,
) -> Meeting:
    return get_meeting_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )


def get_meetings(
    user_keycloak_uuid: UUID,
    search: str | None,
) -> List[Meeting]:
    return get_meetings_service(
        user_keycloak_uuid=user_keycloak_uuid,
        search=search,
    )


def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    user_keycloak_uuid: UUID,
) -> Meeting:
    return update_meeting_service(
        meeting_id=meeting_id,
        meeting_update=meeting_update,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )


async def generate_presigned_audio_upload_url(
    meeting_id: int,
    user_keycloak_uuid: UUID,
    presigned_request: PresignedAudioFileRequest,
) -> str:
    get_meeting_service(
        meeting_id=meeting_id,
        current_user_keycloak_uuid=user_keycloak_uuid,
    )

    return await get_presigned_upload_url(
        meeting_id=meeting_id,
        presigned_request=presigned_request,
    )
