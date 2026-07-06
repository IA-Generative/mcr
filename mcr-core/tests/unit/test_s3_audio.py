"""Behaviour tests for the S3 audio-chunk path (list → download → concatenate).

Runs against the in-memory S3 fake instead of patching the functions'
collaborators, so the tests exercise the real listing/concatenation logic.
"""

import pytest

from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.exceptions.exceptions import (
    InvalidAudioFileError,
    NoAudioFoundError,
)
from mcr_meeting.app.infrastructure.s3 import (
    download_and_concatenate_s3_audio_chunks_into_bytes,
    fetch_audio_bytes,
)
from mcr_meeting.app.schemas.S3_types import S3Object
from tests.mocks.in_memory_s3 import InMemoryS3

_AUDIO_FOLDER = S3Settings().S3_AUDIO_FOLDER


def _put_chunk(fake: InMemoryS3, meeting_id: int, name: str, data: bytes) -> None:
    fake.objects[f"{_AUDIO_FOLDER}/{meeting_id}/{name}"] = data


class TestFetchAudioBytes:
    def test_raises_no_audio_found_when_meeting_has_no_chunks(
        self, in_memory_s3: InMemoryS3
    ) -> None:
        with pytest.raises(
            NoAudioFoundError, match="No audio files found for meeting 123"
        ):
            fetch_audio_bytes(meeting_id=123)

    def test_concatenates_chunks_in_key_order(self, in_memory_s3: InMemoryS3) -> None:
        _put_chunk(in_memory_s3, 123, "chunk_002.weba", b"-two")
        _put_chunk(in_memory_s3, 123, "chunk_001.weba", b"one")

        result = fetch_audio_bytes(meeting_id=123)

        # read() from the returned buffer proves it is rewound to the start
        assert result.read() == b"one-two"

    def test_ignores_chunks_of_other_meetings(self, in_memory_s3: InMemoryS3) -> None:
        _put_chunk(in_memory_s3, 123, "chunk_001.weba", b"mine")
        _put_chunk(in_memory_s3, 1234, "chunk_001.weba", b"not-mine")

        result = fetch_audio_bytes(meeting_id=123)

        assert result.read() == b"mine"

    def test_wraps_download_failure_in_invalid_audio_file_error(
        self, in_memory_s3: InMemoryS3
    ) -> None:
        _put_chunk(in_memory_s3, 123, "chunk_001.weba", b"one")
        in_memory_s3.should_fail_get = True

        with pytest.raises(
            InvalidAudioFileError,
            match="Failed to fetch audio bytes for meeting 123",
        ):
            fetch_audio_bytes(meeting_id=123)


class TestDownloadAndConcatenateS3AudioChunks:
    def test_raises_no_audio_found_on_empty_iterator(self) -> None:
        with pytest.raises(NoAudioFoundError, match="No audio chunks found"):
            download_and_concatenate_s3_audio_chunks_into_bytes(iter([]))

    def test_download_failure_names_the_failing_chunk(
        self, in_memory_s3: InMemoryS3
    ) -> None:
        object_name = f"{_AUDIO_FOLDER}/123/chunk_001.weba"
        in_memory_s3.objects[object_name] = b"one"
        in_memory_s3.should_fail_get = True

        objects = iter(
            [S3Object.model_validate({"Key": object_name, "LastModified": None})]
        )

        with pytest.raises(
            InvalidAudioFileError, match=f"Failed to download audio chunk {object_name}"
        ):
            download_and_concatenate_s3_audio_chunks_into_bytes(objects)
