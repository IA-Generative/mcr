from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.speech_to_text.participants_naming.match_speakers_with_participants import (
    format_segments_for_llm,
    replace_speaker_name_if_available,
)
from mcr_meeting.app.services.speech_to_text.participants_naming.participant_extraction import (
    Participant,
)


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
            DiarizedTranscriptionSegment(
                id=1,
                speaker="Speaker A",
                text="Hello world",
                start=0.0,
                end=1.0,
            )
        ]
        result = format_segments_for_llm(segments)
        assert result == "Speaker A: Hello world"

    def test_should_format_multiple_segments_correctly(self) -> None:
        """Checks that format_segments_for_llm formats multiple segments correctly."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1,
                speaker="Speaker A",
                text="Hello",
                start=0.0,
                end=1.0,
            ),
            DiarizedTranscriptionSegment(
                id=1,
                speaker="Speaker B",
                text="Hi there",
                start=1.0,
                end=2.0,
            ),
        ]
        result = format_segments_for_llm(segments)
        assert result == "Speaker A: Hello\nSpeaker B: Hi there"

    def test_should_handle_special_characters_in_transcription(self) -> None:
        """Checks that format_segments_for_llm handles special characters correctly."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1,
                speaker="Speaker A",
                text="Hello! How's it going? \n New line test. $°",
                start=1.0,
                end=2.0,
            )
        ]
        result = format_segments_for_llm(segments)
        assert result == "Speaker A: Hello! How's it going? \n New line test. $°"


class TestReplaceSpeakerNameIfAvailable:
    """Tests for replace_speaker_name_if_available function."""

    def test_should_replace_speaker_id_with_real_name(self) -> None:
        """Checks that speaker IDs are replaced with real names when available."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="SPEAKER_01", text="Hello", start=0.0, end=1.0
            )
        ]
        participants = [
            Participant(
                speaker_id="SPEAKER_01",
                name="John Doe",
                confidence=1.0,
                association_justification="CONFIRMED",
            )
        ]
        replace_speaker_name_if_available(segments, participants)
        assert segments[0].speaker == "John Doe"

    def test_should_not_replace_speaker_id_if_no_matching_participant(self) -> None:
        """Checks that speaker ID is not replaced if no matching participant is found."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="SPEAKER_01", text="Hello", start=0.0, end=1.0
            )
        ]
        participants = [
            Participant(
                speaker_id="SPEAKER_02",
                name="Jane Doe",
                confidence=1.0,
                association_justification="CONFIRMED",
            )
        ]
        replace_speaker_name_if_available(segments, participants)
        assert segments[0].speaker == "SPEAKER_01"

    def test_should_not_replace_speaker_id_if_participant_name_is_empty(self) -> None:
        """Checks that speaker ID is not replaced if the matching participant name is empty."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="SPEAKER_01", text="Hello", start=0.0, end=1.0
            )
        ]
        participants = [
            Participant(
                speaker_id="SPEAKER_01",
                name="",
                confidence=1.0,
                association_justification="CONFIRMED",
            )
        ]
        replace_speaker_name_if_available(segments, participants)
        assert segments[0].speaker == "SPEAKER_01"

    def test_should_handle_empty_segments(self) -> None:
        """Checks that no error occurs when segments list is empty."""
        segments = []
        participants = [
            Participant(
                speaker_id="SPEAKER_01",
                name="John Doe",
                confidence=1.0,
                association_justification="CONFIRMED",
            )
        ]
        replace_speaker_name_if_available(segments, participants)
        assert segments == []

    def test_should_handle_empty_participants(self) -> None:
        """Checks that no replacement occurs when participants list is empty."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="SPEAKER_01", text="Hello", start=0.0, end=1.0
            )
        ]
        participants = []
        replace_speaker_name_if_available(segments, participants)
        assert segments[0].speaker == "SPEAKER_01"

    def test_should_replace_multiple_segments(self) -> None:
        """Checks that multiple segments with different speakers are correctly replaced."""
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="SPEAKER_01", text="Hello", start=0.0, end=1.0
            ),
            DiarizedTranscriptionSegment(
                id=2, speaker="SPEAKER_02", text="Hi", start=1.0, end=2.0
            ),
            DiarizedTranscriptionSegment(
                id=3, speaker="SPEAKER_01", text="How are you?", start=2.0, end=3.0
            ),
        ]
        participants = [
            Participant(
                speaker_id="SPEAKER_01",
                name="John Doe",
                confidence=1.0,
                association_justification="CONFIRMED",
            ),
            Participant(
                speaker_id="SPEAKER_02",
                name="Jane Smith",
                confidence=1.0,
                association_justification="CONFIRMED",
            ),
        ]
        replace_speaker_name_if_available(segments, participants)
        assert segments[0].speaker == "John Doe"
        assert segments[1].speaker == "Jane Smith"
        assert segments[2].speaker == "John Doe"
