from collections.abc import Generator, Iterator
from io import BytesIO

from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.exceptions.exceptions import (
    MeetingMultipartException,
    NotFoundException,
)
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartBaseRequest,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
    PresignedAudioFileRequest,
    S3Object,
)
from mcr_meeting.app.services.s3_service import (
    abort_multipart_upload as abort_multipart_upload_in_s3,
)
from mcr_meeting.app.services.s3_service import (
    complete_multipart_upload as complete_multipart_upload_in_s3,
)
from mcr_meeting.app.services.s3_service import (
    create_multipart_upload,
    get_audio_object_prefix,
    get_file_from_s3,
    get_file_from_s3_or_none,
    get_objects_list_from_prefix,
    get_presigned_url_for_put_file,
    get_presigned_url_for_upload_part,
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


def download_transcription_docx(meeting_id: int, filename: str | None) -> BytesIO:
    if filename is None:
        raise NotFoundException(
            "Couldn't get transcription as meeting.transcription_filename is empty"
        )
    object_name = get_transcription_object_name(
        meeting_id=meeting_id, filename=filename
    )
    return get_file_from_s3(object_name)


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


def get_report_from_s3(meeting_id: int, filename: str) -> BytesIO:
    object_name = get_report_object_name(meeting_id=meeting_id, filename=filename)
    return get_file_from_s3(object_name)


def get_typed_deliverable_from_s3(
    meeting_id: int, deliverable_type: DeliverableType
) -> BytesIO | None:
    object_name = _object_name_for_deliverable(meeting_id, deliverable_type)
    return get_file_from_s3_or_none(object_name)


def get_transcription_from_s3(meeting_id: int, filename: str) -> BytesIO:
    object_name = get_transcription_object_name(
        meeting_id=meeting_id, filename=filename
    )
    return get_file_from_s3(object_name)


def build_presigned_audio_upload_url(
    meeting_id: int, presigned_request: PresignedAudioFileRequest
) -> str:
    object_name = (
        f"{get_audio_object_prefix(str(meeting_id))}{presigned_request.filename}"
    )
    return get_presigned_url_for_put_file(object_name)


def initiate_multipart_upload(
    meeting_id: int, init_request: MultipartInitRequest
) -> MultipartInitResponse:
    result = create_multipart_upload(meeting_id=meeting_id, init_request=init_request)
    return MultipartInitResponse(
        upload_id=result["upload_id"], object_key=result["key"]
    )


def sign_multipart_part(
    meeting_id: int, sign_request: MultipartSignPartRequest
) -> MultipartSignPartResponse:
    _assert_object_key_belongs_to_meeting(meeting_id, sign_request)
    url = get_presigned_url_for_upload_part(
        object_key=sign_request.object_key,
        upload_id=sign_request.upload_id,
        part_number=sign_request.part_number,
    )
    return MultipartSignPartResponse(url=url)


def complete_multipart_upload(
    meeting_id: int, complete_request: MultipartCompleteRequest
) -> None:
    _assert_object_key_belongs_to_meeting(meeting_id, complete_request)
    complete_multipart_upload_in_s3(complete_request)


def abort_multipart_upload(
    meeting_id: int, abort_request: MultipartAbortRequest
) -> None:
    _assert_object_key_belongs_to_meeting(meeting_id, abort_request)
    abort_multipart_upload_in_s3(
        object_key=abort_request.object_key, upload_id=abort_request.upload_id
    )


def stream_meeting_audio(meeting_id: int) -> tuple[Iterator[bytes], str]:
    objects = validate_object_list(
        get_objects_list_from_prefix(prefix=f"{meeting_id}/")
    )
    return _stream_audio_chunks(objects), AUDIO_MEDIA_TYPE


def _assert_object_key_belongs_to_meeting(
    meeting_id: int, request: MultipartBaseRequest
) -> None:
    expected_prefix = get_audio_object_prefix(str(meeting_id))
    if not request.object_key.startswith(expected_prefix):
        raise MeetingMultipartException("Invalid object key for this meeting.")


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
