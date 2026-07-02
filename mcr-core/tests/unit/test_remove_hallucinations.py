from unittest.mock import Mock, patch

from mcr_meeting.app.domain.transcription.post_process import (
    remove_hallucinations,
)
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


class TestRemoveHallucinations:
    """Tests for the remove_hallucinations function."""

    @patch(
        "mcr_meeting.app.domain.transcription.post_process.TranscriptionForbiddenSentences"
    )
    def test_should_remove_nothing_when_no_forbidden_sentences_present(
        self, mock_settings: Mock
    ) -> None:
        """Checks that regular text is untouched when no forbidden sentences are present."""
        mock_settings.return_value.FORBIDDEN_SENTENCES = ["Forbidden sentence."]

        segments = [
            DiarizedTranscriptionSegment(
                id=0, speaker="Jane", text="Hello world.", start=0.0, end=1.0
            ),
            DiarizedTranscriptionSegment(
                id=1, speaker="John", text="This is a test.", start=1.0, end=2.0
            ),
        ]

        result = remove_hallucinations(segments)

        assert len(result) == 2
        assert result[0].text == "Hello world."
        assert result[1].text == "This is a test."

    @patch(
        "mcr_meeting.app.domain.transcription.post_process.TranscriptionForbiddenSentences"
    )
    def test_should_remove_exact_forbidden_sentences(self, mock_settings: Mock) -> None:
        """Checks that exact forbidden sentences are removed."""
        mock_settings.return_value.FORBIDDEN_SENTENCES = [
            "Merci d'avoir regardé cette vidéo !"
        ]

        segments = [
            DiarizedTranscriptionSegment(
                id=0, speaker="Jane", text="Hello world.", start=0.0, end=1.0
            ),
            DiarizedTranscriptionSegment(
                id=1,
                speaker="Jane",
                text="Merci d'avoir regardé cette vidéo !",
                start=1.0,
                end=2.0,
            ),
        ]

        result = remove_hallucinations(segments)

        assert len(result) == 1
        assert result[0].text == "Hello world."

    @patch(
        "mcr_meeting.app.domain.transcription.post_process.TranscriptionForbiddenSentences"
    )
    def test_should_clean_whitespace(self, mock_settings: Mock) -> None:
        """Checks that extra whitespace is cleaned."""
        mock_settings.return_value.FORBIDDEN_SENTENCES = ["Forbidden."]

        segments = [
            DiarizedTranscriptionSegment(
                id=0,
                speaker="Jane",
                text="  Too   many    spaces  ",
                start=0.0,
                end=1.0,
            ),
        ]

        result = remove_hallucinations(segments)

        assert len(result) == 1
        assert result[0].text == "Too many spaces"

    @patch(
        "mcr_meeting.app.domain.transcription.post_process.TranscriptionForbiddenSentences"
    )
    def test_should_remove_empty_segments(self, mock_settings: Mock) -> None:
        """Checks that segments that become empty after cleaning are removed."""
        mock_settings.return_value.FORBIDDEN_SENTENCES = ["Forbidden."]

        segments = [
            DiarizedTranscriptionSegment(
                id=0, speaker="Jane", text="Forbidden.", start=0.0, end=1.0
            ),
            DiarizedTranscriptionSegment(
                id=1, speaker="Jane", text="  ", start=1.0, end=2.0
            ),
            DiarizedTranscriptionSegment(
                id=2, speaker="John", text="Valid text.", start=2.0, end=3.0
            ),
        ]

        result = remove_hallucinations(segments)

        assert len(result) == 1
        assert result[0].text == "Valid text."
        assert result[0].id == 2

    @patch(
        "mcr_meeting.app.domain.transcription.post_process.TranscriptionForbiddenSentences"
    )
    def test_should_remove_forbidden_sentences_middle_of_text(
        self, mock_settings: Mock
    ) -> None:
        """Checks that forbidden sentences are removed from the middle of segment text."""
        mock_settings.return_value.FORBIDDEN_SENTENCES = ["HALLUCINATION"]

        segments = [
            DiarizedTranscriptionSegment(
                id=0,
                speaker="Jane",
                text="Start of sentence HALLUCINATION end of sentence.",
                start=0.0,
                end=5.0,
            ),
        ]

        result = remove_hallucinations(segments)

        assert len(result) == 1
        assert result[0].text == "Start of sentence end of sentence."
