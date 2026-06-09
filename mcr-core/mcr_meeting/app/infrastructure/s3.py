from collections.abc import Generator, Iterator
from io import BytesIO

from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.schemas.S3_types import PresignedAudioFileRequest, S3Object
from mcr_meeting.app.services.s3_service import (
    get_audio_object_prefix,
    get_file_from_s3,
    get_objects_list_from_prefix,
    get_presigned_url_for_put_file,
    get_report_object_name,
    put_file_to_s3,
    validate_object_list,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE

s3_settings = S3Settings()

AUDIO_MEDIA_TYPE = "audio/webm"


def get_transcription_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_TRANSCRIPTION_FOLDER}/{meeting_id}/{filename}"


def upload_transcription_to_s3(
    meeting_id: int,
    filename: str,
    content: BytesIO,
) -> str:
    object_name = get_transcription_object_name(
        meeting_id=meeting_id, filename=filename
    )
    put_file_to_s3(
        content=content,
        object_name=object_name,
        content_type=DOCX_MIME_TYPE,
    )
    return object_name


def upload_report_to_s3(
    meeting_id: int,
    deliverable_type: DeliverableType,
    content: BytesIO,
) -> str:
    object_name = _object_name_for_deliverable(meeting_id, deliverable_type)
    put_file_to_s3(
        content=content,
        object_name=object_name,
        content_type=DOCX_MIME_TYPE,
    )
    return object_name


def build_presigned_audio_upload_url(
    meeting_id: int, presigned_request: PresignedAudioFileRequest
) -> str:
    object_name = (
        f"{get_audio_object_prefix(str(meeting_id))}{presigned_request.filename}"
    )
    return get_presigned_url_for_put_file(object_name)


def stream_meeting_audio(meeting_id: int) -> tuple[Iterator[bytes], str]:
    objects = validate_object_list(
        get_objects_list_from_prefix(prefix=f"{meeting_id}/")
    )
    return _stream_audio_chunks(objects), AUDIO_MEDIA_TYPE


def _object_name_for_deliverable(
    meeting_id: int, deliverable_type: DeliverableType
) -> str:
    filename = f"{deliverable_type.lower()}.docx"
    return get_report_object_name(meeting_id=meeting_id, filename=filename)


def _stream_audio_chunks(
    obj_iterator: Iterator[S3Object],
) -> Generator[bytes, None, None]:
    for obj_info in obj_iterator:
        audio_chunk_data = get_file_from_s3(object_name=obj_info.object_name)
        yield audio_chunk_data.read()
