from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    assemble_normalized_wav_from_s3_chunks,
)


class TestAssembleNormalizedWavFromS3Chunks:
    """Tests for the function assemble_normalized_wav_from_s3_chunks."""

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.normalize_audio_bytes_to_wav_bytes"
    )
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_raise_invalid_audio_file_error_when_download_fails(
        self, mock_download: Mock, mock_normalize: Mock
    ) -> None:
        """Checks that the function handles download failures."""
        mock_download.side_effect = InvalidAudioFileError(
            "No audio chunks found to process"
        )

        empty_chunk_list = [Mock()]

        with pytest.raises(
            InvalidAudioFileError, match="No audio chunks found to process"
        ):
            assemble_normalized_wav_from_s3_chunks(iter(empty_chunk_list))

        mock_normalize.assert_not_called()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_return_normalized_audio_bytes_when_successful_with_filtering(
        self, mock_download: Mock
    ) -> None:
        """Checks successful assembly returns the concatenated audio bytes."""

        expected_audio_bytes = BytesIO(b"raw_audio")
        mock_download.return_value = expected_audio_bytes

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects))

        assert result == expected_audio_bytes
        mock_download.assert_called_once()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_handle_multiple_s3_objects(self, mock_download: Mock) -> None:
        """Checks that the function handles multiple S3 objects correctly."""

        expected_audio = BytesIO(b"concatenated_audio")
        mock_download.return_value = expected_audio

        s3_objects = [Mock(), Mock(), Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects))

        assert result == expected_audio
        mock_download.assert_called_once()

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_return_audio_bytes_directly(self, mock_download: Mock) -> None:
        """Checks that the function returns audio bytes directly from download."""

        audio_bytes = BytesIO(b"audio_data")
        mock_download.return_value = audio_bytes

        s3_objects = [Mock()]

        result = assemble_normalized_wav_from_s3_chunks(iter(s3_objects))

        assert result == audio_bytes
        mock_download.assert_called_once()
