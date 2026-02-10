from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
from mcr_meeting.app.services.meeting_to_transcription_service import (
    fetch_audio_bytes,
    format_segments_for_llm,
)


class TestFetchAudioBytes:
    """Tests pour la fonction fetch_audio_bytes."""

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    def test_should_raise_invalid_audio_file_error_when_no_audio_files_found(
        self, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes raises ValueError when no audio files are found."""
        mock_get_objects_list.return_value = iter([])

        with pytest.raises(ValueError, match="No audio files found for meeting 123"):
            fetch_audio_bytes(meeting_id=123)

        mock_get_objects_list.assert_called_once_with(prefix="123/")

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_raise_invalid_audio_file_error_when_audio_processing_fails(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes raises Exception when audio processing fails."""
        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.side_effect = InvalidAudioFileError("Processing failed")

        with pytest.raises(Exception, match="Audio processing failed for meeting 123"):
            fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_raise_invalid_audio_file_error_when_extension_extraction_fails(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes raises ValueError when extension extraction fails."""
        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.side_effect = ValueError(
            "No audio files found for the specified meeting"
        )

        with pytest.raises(ValueError, match="No audio files found for meeting 123"):
            fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_raise_invalid_audio_file_error_when_unexpected_error_occurs(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes raises Exception for any unexpected error."""
        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(
            Exception, match="Failed to fetch audio bytes for meeting 123"
        ):
            fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_return_audio_bytes_when_successful(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes returns audio bytes when successful."""

        expected_audio_bytes = BytesIO(b"audio_data_normalized_12345")

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = expected_audio_bytes

        result = fetch_audio_bytes(meeting_id=123)

        assert result == expected_audio_bytes
        mock_get_objects_list.assert_called_once_with(prefix="123/")
        mock_assemble.assert_called_once()

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_handle_different_audio_extensions(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes handles different audio extensions correctly."""

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = BytesIO(b"audio_data")

        # Since the service no longer deals with extensions directly,
        # we just test that it processes the audio correctly
        result = fetch_audio_bytes(meeting_id=123)
        assert result.getvalue() == b"audio_data"
        mock_assemble.assert_called_once()

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_handle_different_error_types_from_assemble(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes handles different error types from download_and_concatenate_s3_audio_chunks_into_bytes correctly."""
        mock_get_objects_list.return_value = iter([Mock()])

        error_test_cases = [
            InvalidAudioFileError("No audio chunks found"),
            InvalidAudioFileError("FFmpeg failed"),
            InvalidAudioFileError("Normalization error"),
        ]

        for error in error_test_cases:
            mock_assemble.side_effect = error

            with pytest.raises(Exception):
                fetch_audio_bytes(meeting_id=123)

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_handle_empty_audio_bytes(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes handles empty audio bytes correctly."""

        mock_get_objects_list.return_value = iter([Mock()])
        mock_assemble.return_value = BytesIO(b"")

        result = fetch_audio_bytes(meeting_id=123)

        assert result.getvalue() == b""

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.download_and_concatenate_s3_audio_chunks_into_bytes"
    )
    def test_should_handle_large_audio_files(
        self, mock_assemble: Mock, mock_get_objects_list: Mock
    ) -> None:
        """Checks that fetch_audio_bytes handles large audio files correctly."""

        mock_get_objects_list.return_value = iter([Mock()])

        large_audio_data = b"x" * (5 * 1024 * 1024)
        mock_assemble.return_value = BytesIO(large_audio_data)

        result = fetch_audio_bytes(meeting_id=123)

        assert result.getvalue() == large_audio_data
        assert len(result.getvalue()) == 5 * 1024 * 1024

    @patch(
        "mcr_meeting.app.services.meeting_to_transcription_service.get_objects_list_from_prefix"
    )
    def test_should_call_get_objects_list_with_correct_prefix_format(
        self, mock_get_objects_list: Mock
    ) -> None:
        """Checks that get_objects_list_from_prefix is called with the correct prefix format."""
        mock_get_objects_list.return_value = iter([])

        meeting_id = 42
        with pytest.raises(ValueError):
            fetch_audio_bytes(meeting_id=meeting_id)

        mock_get_objects_list.assert_called_once_with(prefix="42/")

        for test_id in [1, 999, 123456]:
            mock_get_objects_list.reset_mock()
            with pytest.raises(ValueError):
                fetch_audio_bytes(meeting_id=test_id)
            mock_get_objects_list.assert_called_once_with(prefix=f"{test_id}/")


class TestFormatSegmentsForLLM:
    """Tests for format_segments_for_llm function."""

    def test_should_return_empty_string_when_no_segments(self) -> None:
        """Checks that format_segments_for_llm returns an empty string when no segments are provided."""
        segments = []
        result = format_segments_for_llm(segments)
        assert result == ""

    def test_should_format_single_segment_correctly(self) -> None:
        """Checks that format_segments_for_llm formats a single segment correctly."""
        segments = [
            SpeakerTranscription(
                meeting_id=1,
                speaker="Speaker A",
                transcription_index=0,
                transcription="Hello world",
                start=0.0,
                end=1.0,
            )
        ]
        result = format_segments_for_llm(segments)
        assert result == "Speaker A: Hello world"

    def test_should_format_multiple_segments_correctly(self) -> None:
        """Checks that format_segments_for_llm formats multiple segments correctly."""
        segments = [
            SpeakerTranscription(
                meeting_id=1,
                speaker="Speaker A",
                transcription_index=0,
                transcription="Hello",
                start=0.0,
                end=1.0,
            ),
            SpeakerTranscription(
                meeting_id=1,
                speaker="Speaker B",
                transcription_index=1,
                transcription="Hi there",
                start=1.0,
                end=2.0,
            ),
        ]
        result = format_segments_for_llm(segments)
        assert result == "Speaker A: Hello\nSpeaker B: Hi there"

    def test_should_handle_special_characters_in_transcription(self) -> None:
        """Checks that format_segments_for_llm handles special characters correctly."""
        segments = [
            SpeakerTranscription(
                meeting_id=1,
                speaker="Speaker A",
                transcription_index=0,
                transcription="Hello! How's it going? \n New line test.",
                start=0.0,
                end=1.0,
            )
        ]
        result = format_segments_for_llm(segments)
        assert result == "Speaker A: Hello! How's it going? \n New line test."
