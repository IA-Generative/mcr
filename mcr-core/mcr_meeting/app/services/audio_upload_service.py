from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.schemas.S3_types import PresignedAudioFileRequest
from mcr_meeting.app.services.s3_service import (
    get_audio_object_prefix,
    get_presigned_url_for_put_file,
)

s3_settings = S3Settings()


async def get_presigned_upload_url(
    meeting_id: int, presigned_request: PresignedAudioFileRequest
) -> str:
    """
    Generates a presigned URL for uploading an audio file to S3.
    """

    object_name = (
        f"{get_audio_object_prefix(str(meeting_id))}{presigned_request.filename}"
    )

    return get_presigned_url_for_put_file(object_name)
