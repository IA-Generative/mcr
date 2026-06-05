from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.infrastructure.s3 import build_presigned_audio_upload_url
from mcr_meeting.app.schemas.S3_types import PresignedAudioFileRequest


def generate_presigned_audio_upload_url(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
    presigned_request: PresignedAudioFileRequest,
) -> str:
    meeting = get_meeting_by_id(meeting_id, with_deliverables=True)
    authorize_meeting_access(meeting, user_keycloak_uuid)
    return build_presigned_audio_upload_url(meeting_id, presigned_request)
