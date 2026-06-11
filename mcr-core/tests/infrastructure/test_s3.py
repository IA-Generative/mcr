from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import MeetingMultipartException
from mcr_meeting.app.infrastructure.s3 import (
    _stream_audio_chunks,
    abort_multipart_upload,
    complete_multipart_upload,
    initiate_multipart_upload,
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


@patch("mcr_meeting.app.infrastructure.s3.get_file_from_s3")
@patch("mcr_meeting.app.infrastructure.s3.validate_object_list")
@patch("mcr_meeting.app.infrastructure.s3.get_objects_list_from_prefix")
def test_stream_meeting_audio_returns_iterator_and_media_type(
    mock_get_objects: Mock, mock_validate: Mock, mock_get_file: Mock
) -> None:
    # Arrange
    s3_obj = S3Object(
        bucket_name="test-bucket",
        object_name="1/1234.weba",
        last_modified=None,
    )
    mock_get_objects.return_value = iter([s3_obj])
    mock_validate.return_value = iter([s3_obj])
    mock_get_file.return_value = BytesIO(b"fake_audio")

    # Act
    iterator, media_type = stream_meeting_audio(1)

    # Assert
    assert media_type == "audio/webm"
    assert list(iterator) == [b"fake_audio"]
    mock_get_objects.assert_called_once_with(prefix="1/")


@patch("mcr_meeting.app.infrastructure.s3.get_objects_list_from_prefix")
def test_stream_meeting_audio_raises_when_no_audio_files(
    mock_get_objects: Mock,
) -> None:
    # Arrange — empty listing makes validate_object_list raise eagerly
    mock_get_objects.return_value = iter([])

    # Act & Assert
    with pytest.raises(ValueError, match="No audio files found"):
        stream_meeting_audio(1)


@patch("mcr_meeting.app.infrastructure.s3.get_file_from_s3")
def test_stream_audio_chunks_yields_bytes_in_order(mock_get_file: Mock) -> None:
    # Arrange
    mock_get_file.side_effect = [
        BytesIO(b"chunk_1"),
        BytesIO(b"chunk_2"),
        BytesIO(b"chunk_3"),
    ]
    s3_objects = [
        S3Object(bucket_name="b", object_name=f"1/{i}.weba", last_modified=None)
        for i in range(3)
    ]

    # Act
    result = list(_stream_audio_chunks(iter(s3_objects)))

    # Assert
    assert result == [b"chunk_1", b"chunk_2", b"chunk_3"]
    assert mock_get_file.call_count == 3


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
