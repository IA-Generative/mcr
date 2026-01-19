from io import BytesIO

from mcr_capture_worker.schemas.audio_capture_schema import (
    S3Object,
)
from mcr_capture_worker.settings.settings import S3Settings
from mcr_capture_worker.utils.s3_client import s3_client
from mcr_capture_worker.utils.s3_service import (
    get_audio_object_prefix,
    get_trace_object_prefix,
)

s3_settings = S3Settings()


async def put_file_in_trace_folder(
    data: BytesIO, meeting_id: int, filename: str, content_type: str = "application/zip"
) -> S3Object:
    object_name = f"{get_trace_object_prefix(str(meeting_id))}{filename}"

    return await _put_file_in_s3(data, object_name, content_type)


async def put_file_in_audio_folder(
    data: BytesIO, meeting_id: int, filename: str, content_type: str = "audio/weba"
) -> S3Object:
    object_name = f"{get_audio_object_prefix(str(meeting_id))}{filename}"

    return await _put_file_in_s3(data, object_name, content_type)


async def _put_file_in_s3(
    data: BytesIO, object_name: str, content_type: str
) -> S3Object:
    s3_client.put_object(
        Bucket=s3_settings.S3_BUCKET,
        Key=object_name,
        Body=data,
        ContentType=content_type,
    )

    return S3Object(object_name=object_name, bucket_name=s3_settings.S3_BUCKET)
