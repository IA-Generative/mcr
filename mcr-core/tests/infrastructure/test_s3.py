from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.infrastructure.s3 import _stream_audio_chunks, stream_meeting_audio
from mcr_meeting.app.schemas.S3_types import S3Object


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
