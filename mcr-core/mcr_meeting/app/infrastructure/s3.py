import itertools
from collections.abc import Generator, Iterable, Iterator
from io import BytesIO
from typing import cast

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ConnectionError as BotoConnectionError,
)
from botocore.exceptions import (
    ConnectTimeoutError,
    ReadTimeoutError,
    ResponseStreamingError,
)
from loguru import logger
from mypy_boto3_s3 import S3Client
from mypy_boto3_s3.type_defs import CompletedPartTypeDef
from pydantic import TypeAdapter
from urllib3.exceptions import IncompleteRead, ProtocolError

from mcr_meeting.app.configs.base import RetrySettings, S3Settings
from mcr_meeting.app.domain.mime_types import DOCX_MIME_TYPE, guess_mime_type
from mcr_meeting.app.exceptions.exceptions import (
    MeetingMultipartException,
    NoAudioFoundError,
    S3TransientError,
)
from mcr_meeting.app.infrastructure.retry import retry_transient
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartBaseRequest,
    MultipartCompleteRequest,
    MultipartCreationObject,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
    PresignedAudioFileRequest,
    S3ListObjectsPage,
    S3Object,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    DiarizedTranscriptionSegment,
    FullTranscript,
)

s3_settings = S3Settings()
_retry_settings = RetrySettings()

_boto_config = Config(
    connect_timeout=_retry_settings.S3_CONNECT_TIMEOUT,
    read_timeout=_retry_settings.S3_READ_TIMEOUT,
    retries={"total_max_attempts": 1},
)

_endpoint_url = s3_settings.S3_ENDPOINT
if not _endpoint_url.startswith(("http://", "https://")):
    _endpoint_url = f"http://{_endpoint_url}"

_use_ssl = _endpoint_url.startswith("https://")

s3_client: S3Client = boto3.client(
    service_name="s3",
    use_ssl=_use_ssl,
    endpoint_url=_endpoint_url,
    aws_access_key_id=s3_settings.S3_ACCESS_KEY,
    aws_secret_access_key=s3_settings.S3_SECRET_KEY,
    region_name=s3_settings.S3_REGION,
    config=_boto_config,
)

# Create an "external" client to generate the presigned URL
# This client cannot reach the server from inside the cluster, as it is using the S3_EXTERNAL_ENDPOINT
s3_external_client: S3Client = boto3.client(
    service_name="s3",
    use_ssl=_use_ssl,
    endpoint_url=s3_settings.S3_EXTERNAL_ENDPOINT,
    aws_access_key_id=s3_settings.S3_ACCESS_KEY,
    aws_secret_access_key=s3_settings.S3_SECRET_KEY,
    region_name=s3_settings.S3_REGION,
    config=_boto_config,
)

S3_TRANSIENT = (
    ResponseStreamingError,
    ReadTimeoutError,
    ConnectTimeoutError,
    BotoConnectionError,
    ProtocolError,
    IncompleteRead,
)

_with_retry_transient = retry_transient(
    on=(S3TransientError,),
    attempts=_retry_settings.S3_RETRY_ATTEMPTS,
    initial_delay=_retry_settings.S3_RETRY_INITIAL_DELAY,
    max_delay=_retry_settings.S3_RETRY_MAX_DELAY,
)

AUDIO_MEDIA_TYPE = "audio/webm"

_JSON_CONTENT_TYPE = "application/json"
_WAV_CONTENT_TYPE = "audio/wav"

_DIARIZATION_LIST_SERIALIZER = TypeAdapter(list[DiarizationSegment])
_TRANSCRIPTION_RAW_LIST_SERIALIZER = TypeAdapter(list[DiarizedTranscriptionSegment])


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


def download_transcription_docx(meeting_id: int, filename: str) -> BytesIO:
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


def fetch_audio_bytes(meeting_id: int) -> BytesIO:
    logger.info("Fetching audio bytes for meeting ID: {}", meeting_id)

    try:
        chunks = get_objects_list_from_prefix(prefix=f"{meeting_id}/")
        return download_and_concatenate_s3_audio_chunks_into_bytes(chunks)
    except NoAudioFoundError as no_files_error:
        raise NoAudioFoundError(
            f"No audio files found for meeting {meeting_id}"
        ) from no_files_error


def download_and_concatenate_s3_audio_chunks_into_bytes(
    objects: Iterable[S3Object],
) -> BytesIO:
    audio_buffer = BytesIO()
    chunk_count = 0

    for obj_info in objects:
        chunk_count += 1
        audio_chunk_data = get_file_from_s3(object_name=obj_info.object_name)
        audio_buffer.write(audio_chunk_data.read())

    if chunk_count == 0:
        raise NoAudioFoundError("No audio chunks found in iterator")

    audio_buffer.seek(0)
    return audio_buffer


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
    objects: Iterable[S3Object],
) -> Generator[bytes, None, None]:
    for obj_info in objects:
        audio_chunk_data = get_file_from_s3(object_name=obj_info.object_name)
        yield audio_chunk_data.read()


def get_artifact_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_ARTIFACTS_FOLDER}/{meeting_id}/{filename}"


def get_preprocessed_audio_object_name(meeting_id: int) -> str:
    return get_artifact_object_name(meeting_id, "preprocessed_audio.wav")


def get_diarization_object_name(meeting_id: int) -> str:
    return get_artifact_object_name(meeting_id, "diarization.json")


def get_transcription_raw_object_name(meeting_id: int) -> str:
    return get_artifact_object_name(meeting_id, "transcription_raw.json")


def write_preprocessed_audio(meeting_id: int, preprocessed_audio: BytesIO) -> None:
    preprocessed_audio.seek(0)
    put_file_to_s3(
        preprocessed_audio,
        get_preprocessed_audio_object_name(meeting_id),
        _WAV_CONTENT_TYPE,
    )


def read_preprocessed_audio(meeting_id: int) -> BytesIO:
    return get_file_from_s3(get_preprocessed_audio_object_name(meeting_id))


def write_diarization(meeting_id: int, diarization: list[DiarizationSegment]) -> None:
    put_file_to_s3(
        BytesIO(_DIARIZATION_LIST_SERIALIZER.dump_json(diarization)),
        get_diarization_object_name(meeting_id),
        _JSON_CONTENT_TYPE,
    )


def read_diarization(meeting_id: int) -> list[DiarizationSegment]:
    return _DIARIZATION_LIST_SERIALIZER.validate_json(
        get_file_from_s3(get_diarization_object_name(meeting_id)).getvalue()
    )


def write_transcription_raw(
    meeting_id: int, segments: list[DiarizedTranscriptionSegment]
) -> None:
    put_file_to_s3(
        BytesIO(_TRANSCRIPTION_RAW_LIST_SERIALIZER.dump_json(segments)),
        get_transcription_raw_object_name(meeting_id),
        _JSON_CONTENT_TYPE,
    )


def read_transcription_raw(
    meeting_id: int,
) -> list[DiarizedTranscriptionSegment]:
    return _TRANSCRIPTION_RAW_LIST_SERIALIZER.validate_json(
        get_file_from_s3(get_transcription_raw_object_name(meeting_id)).getvalue()
    )


def get_full_transcript_object_name(meeting_id: int) -> str:
    return get_transcription_object_name(meeting_id, "full_transcript.json")


def write_full_transcript(full_transcript: FullTranscript) -> None:
    put_file_to_s3(
        BytesIO(full_transcript.model_dump_json().encode()),
        get_full_transcript_object_name(full_transcript.meeting_id),
        _JSON_CONTENT_TYPE,
    )


def read_full_transcript(meeting_id: int) -> FullTranscript:
    return FullTranscript.model_validate_json(
        get_file_from_s3(get_full_transcript_object_name(meeting_id)).getvalue()
    )


@_with_retry_transient
def get_file_from_s3(object_name: str) -> BytesIO:
    try:
        response = s3_client.get_object(Bucket=s3_settings.S3_BUCKET, Key=object_name)
        return BytesIO(response["Body"].read())
    except S3_TRANSIENT as e:
        raise S3TransientError(f"Transient error for s3 read: {object_name}") from e


def get_file_from_s3_or_none(object_name: str) -> BytesIO | None:
    try:
        return get_file_from_s3(object_name)
    except s3_client.exceptions.NoSuchKey:
        return None


def get_presigned_url_for_put_file(name: str) -> str:
    return s3_external_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": s3_settings.S3_BUCKET, "Key": name},
        ExpiresIn=3600,  # 1 hour
    )


def create_multipart_upload(
    meeting_id: int,
    init_request: MultipartInitRequest,
) -> MultipartCreationObject:
    """
    Initialize an S3 multipart upload and return the upload id and key.
    """
    object_key = get_audio_object_name(meeting_id, init_request.filename)
    content_type = init_request.content_type or guess_mime_type(init_request.filename)

    response = s3_client.create_multipart_upload(
        Bucket=s3_settings.S3_BUCKET,
        Key=object_key,
        ContentType=content_type,
    )
    return {
        "upload_id": response["UploadId"],
        "key": response["Key"],
        "bucket": s3_settings.S3_BUCKET,
    }


def get_presigned_url_for_upload_part(
    object_key: str, upload_id: str, part_number: int
) -> str:
    """
    Generate a presigned URL for uploading one part of a multipart upload.
    """
    return s3_external_client.generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": s3_settings.S3_BUCKET,
            "Key": object_key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=3600,  # 1 hour
    )


def complete_multipart_upload_in_s3(complete_request: MultipartCompleteRequest) -> None:
    """
    Complete an S3 multipart upload with the list of parts:
    parts = [{ 'ETag': '<etag-from-upload>', 'PartNumber': <int> }, ...]
    """
    s3_client.complete_multipart_upload(
        Bucket=s3_settings.S3_BUCKET,
        Key=complete_request.object_key,
        UploadId=complete_request.upload_id,
        MultipartUpload={
            "Parts": cast(
                list[CompletedPartTypeDef],
                [part.model_dump(by_alias=True) for part in complete_request.parts],
            )
        },
    )


def abort_multipart_upload_in_s3(object_key: str, upload_id: str) -> None:
    """
    Abort a previously initiated S3 multipart upload.
    """
    s3_client.abort_multipart_upload(
        Bucket=s3_settings.S3_BUCKET, Key=object_key, UploadId=upload_id
    )


@_with_retry_transient
def _list_objects_under_prefix(prefix: str) -> list[S3Object]:
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(
            Bucket=s3_settings.S3_BUCKET, Prefix=get_audio_object_prefix(prefix)
        )
        objects: list[S3Object] = []
        for page in page_iterator:
            objects.extend(S3ListObjectsPage.model_validate(page).contents)
        return objects
    except S3_TRANSIENT as e:
        raise S3TransientError(f"Transient error for s3 list: {prefix}") from e


def get_objects_list_from_prefix(prefix: str) -> list[S3Object]:
    return sorted(_list_objects_under_prefix(prefix), key=lambda o: o.object_name)


def validate_object_list(objects: Iterable[S3Object]) -> Iterator[S3Object]:
    it = iter(objects)
    try:
        first_object = next(it)
        return itertools.chain([first_object], it)
    except StopIteration:
        logger.error("No audio files found in S3 iterator")
        raise ValueError("No audio files found for the specified meeting")


@_with_retry_transient
def put_file_to_s3(
    content: BytesIO,
    object_name: str,
    content_type: str = "application/octet-stream",
) -> None:
    try:
        content.seek(0)
        s3_client.put_object(
            Bucket=s3_settings.S3_BUCKET,
            Key=object_name,
            Body=content,
            ContentType=content_type,
        )
    except S3_TRANSIENT as e:
        raise S3TransientError(f"Transient error for s3 upload: {object_name}") from e


def get_report_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_REPORT_FOLDER}/{meeting_id}/{filename}"


def get_evaluation_dataset_object_name(filename: str) -> str:
    return f"{s3_settings.S3_EVALUATION_DATASET_FOLDER}/{filename}"


def get_audio_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_AUDIO_FOLDER}/{meeting_id}/{filename}"


def get_audio_object_prefix(meeting_id: str) -> str:
    normalized_meeting_id = str(meeting_id).strip("/")
    return f"{s3_settings.S3_AUDIO_FOLDER}/{normalized_meeting_id}/"
