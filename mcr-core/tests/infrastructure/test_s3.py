from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import (
    MeetingMultipartException,
    S3TransientError,
)
from mcr_meeting.app.infrastructure.s3 import (
    _stream_audio_chunks,
    abort_multipart_upload,
    complete_multipart_upload,
    get_file_from_s3,
    get_file_from_s3_or_none,
    get_objects_list_from_prefix,
    initiate_multipart_upload,
    put_file_to_s3,
    sign_multipart_part,
    stream_meeting_audio,
)
from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartCompletePart,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartSignPartRequest,
    S3Object,
)
from tests.mocks.in_memory_s3 import InMemoryS3, S3Op, transient_error


def test_stream_meeting_audio_returns_chunks_in_key_order(
    in_memory_s3: InMemoryS3,
) -> None:
    in_memory_s3.objects["audio/1/chunk_002.weba"] = b"-two"
    in_memory_s3.objects["audio/1/chunk_001.weba"] = b"one"

    iterator, media_type = stream_meeting_audio(1)

    assert media_type == "audio/webm"
    assert list(iterator) == [b"one", b"-two"]


def test_stream_meeting_audio_raises_when_no_audio_files(
    in_memory_s3: InMemoryS3,
) -> None:
    with pytest.raises(ValueError, match="No audio files found"):
        stream_meeting_audio(1)


def test_stream_audio_chunks_yields_bytes_in_order(in_memory_s3: InMemoryS3) -> None:
    s3_objects = []
    for i in range(3):
        key = f"audio/1/chunk_{i}.weba"
        in_memory_s3.objects[key] = f"chunk_{i}".encode()
        s3_objects.append(
            S3Object(bucket_name="b", object_name=key, last_modified=None)
        )

    result = list(_stream_audio_chunks(iter(s3_objects)))

    assert result == [b"chunk_0", b"chunk_1", b"chunk_2"]


def test_stream_audio_chunks_with_empty_iterator() -> None:
    # Act
    result = list(_stream_audio_chunks(iter([])))

    # Assert
    assert result == []


@patch("mcr_meeting.app.infrastructure.s3.create_multipart_upload")
def test_initiate_multipart_upload_returns_upload_id_and_key(
    mock_create: Mock,
) -> None:
    # Arrange
    mock_create.return_value = {
        "upload_id": "1",
        "key": "audio/1/audio.mp3",
        "bucket": "test-bucket",
    }
    init_request = MultipartInitRequest(filename="audio.mp3")

    # Act
    result = initiate_multipart_upload(1, init_request)

    # Assert
    assert result.upload_id == "1"
    assert result.object_key == "audio/1/audio.mp3"
    mock_create.assert_called_once_with(meeting_id=1, init_request=init_request)


@patch("mcr_meeting.app.infrastructure.s3.get_audio_object_prefix")
@patch("mcr_meeting.app.infrastructure.s3.get_presigned_url_for_upload_part")
def test_sign_multipart_part_returns_presigned_url(
    mock_presigned: Mock, mock_prefix: Mock
) -> None:
    # Arrange
    mock_prefix.return_value = "audio/1/"
    mock_presigned.return_value = "https://presigned"
    sign_request = MultipartSignPartRequest(
        upload_id="1", object_key="audio/1/audio.mp3", part_number=2
    )

    # Act
    result = sign_multipart_part(1, sign_request)

    # Assert
    assert result.url == "https://presigned"
    mock_presigned.assert_called_once_with(
        object_key="audio/1/audio.mp3", upload_id="1", part_number=2
    )


@patch("mcr_meeting.app.infrastructure.s3.get_audio_object_prefix")
def test_sign_multipart_part_rejects_foreign_object_key(mock_prefix: Mock) -> None:
    # Arrange — object_key belongs to a different meeting prefix
    mock_prefix.return_value = "audio/1/"
    sign_request = MultipartSignPartRequest(
        upload_id="1", object_key="audio/2/audio.mp3", part_number=1
    )

    # Act & Assert
    with pytest.raises(MeetingMultipartException):
        sign_multipart_part(1, sign_request)


@patch("mcr_meeting.app.infrastructure.s3.get_audio_object_prefix")
@patch("mcr_meeting.app.infrastructure.s3.complete_multipart_upload_in_s3")
def test_complete_multipart_upload_delegates_to_s3(
    mock_complete: Mock, mock_prefix: Mock
) -> None:
    # Arrange
    mock_prefix.return_value = "audio/1/"
    complete_request = MultipartCompleteRequest(
        upload_id="1",
        object_key="audio/1/audio.mp3",
        parts=[MultipartCompletePart(part_number=1, etag="etag1")],
    )

    # Act
    complete_multipart_upload(1, complete_request)

    # Assert
    mock_complete.assert_called_once_with(complete_request)


@patch("mcr_meeting.app.infrastructure.s3.get_audio_object_prefix")
@patch("mcr_meeting.app.infrastructure.s3.abort_multipart_upload_in_s3")
def test_abort_multipart_upload_delegates_to_s3(
    mock_abort: Mock, mock_prefix: Mock
) -> None:
    # Arrange
    mock_prefix.return_value = "audio/1/"
    abort_request = MultipartAbortRequest(upload_id="1", object_key="audio/1/audio.mp3")

    # Act
    abort_multipart_upload(1, abort_request)

    # Assert
    mock_abort.assert_called_once_with(object_key="audio/1/audio.mp3", upload_id="1")


_ALWAYS_FAIL = 999
_KEY = "audio/1/chunk.weba"


def test_s3_read_absorbs_a_transient_blip(in_memory_s3: InMemoryS3) -> None:
    in_memory_s3.objects[_KEY] = b"audio-bytes"
    in_memory_s3.fail(S3Op.GET, transient_error(), times=1)

    assert get_file_from_s3(_KEY).getvalue() == b"audio-bytes"


def test_s3_read_persistent_failure_surfaces_as_s3_transient(
    in_memory_s3: InMemoryS3,
) -> None:
    in_memory_s3.objects[_KEY] = b"audio-bytes"
    in_memory_s3.fail(S3Op.GET, transient_error(), times=_ALWAYS_FAIL)

    with pytest.raises(S3TransientError):
        get_file_from_s3(_KEY)


def test_s3_read_of_missing_key_is_not_retried(in_memory_s3: InMemoryS3) -> None:
    assert get_file_from_s3_or_none("missing") is None
    assert in_memory_s3.calls[S3Op.GET] == 1


def test_s3_retried_put_stores_the_full_body(in_memory_s3: InMemoryS3) -> None:
    in_memory_s3.fail(S3Op.PUT, transient_error(), times=1)

    put_file_to_s3(BytesIO(b"audio-bytes"), _KEY)

    assert in_memory_s3.objects[_KEY] == b"audio-bytes"


def test_s3_put_persistent_failure_surfaces_as_s3_transient(
    in_memory_s3: InMemoryS3,
) -> None:
    in_memory_s3.fail(S3Op.PUT, transient_error(), times=_ALWAYS_FAIL)

    with pytest.raises(S3TransientError):
        put_file_to_s3(BytesIO(b"audio-bytes"), _KEY)
    assert in_memory_s3.objects == {}


def test_s3_list_absorbs_a_transient_blip(in_memory_s3: InMemoryS3) -> None:
    in_memory_s3.objects["audio/1/chunk.weba"] = b"one"
    in_memory_s3.fail(S3Op.LIST, transient_error(), times=1)

    result = get_objects_list_from_prefix("1/")

    assert [o.object_name for o in result] == ["audio/1/chunk.weba"]


def test_s3_list_persistent_failure_surfaces_as_s3_transient(
    in_memory_s3: InMemoryS3,
) -> None:
    in_memory_s3.fail(S3Op.LIST, transient_error(), times=_ALWAYS_FAIL)

    with pytest.raises(S3TransientError):
        get_objects_list_from_prefix("1/")
