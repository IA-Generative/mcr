from mcr_meeting.app.domain.transcription.participant_reconciliation import (
    detect_name_losses,
    format_segments_as_dialogue,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
)


def _participant(speaker_id: str, name: str | None) -> Participant:
    return Participant(
        speaker_id=speaker_id,
        name=name,
        role=None,
        confidence=0.9,
        association_justification=None,
    )


class TestFormatParticipantsInput:
    def test_joins_segment_str_with_newlines(self) -> None:
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="Speaker A", text="Hello", start=0.0, end=1.0
            ),
            DiarizedTranscriptionSegment(
                id=2, speaker="Speaker B", text="Hi there", start=1.0, end=2.0
            ),
        ]

        assert (
            format_segments_as_dialogue(segments)
            == "Speaker A: Hello\nSpeaker B: Hi there"
        )

    def test_returns_empty_string_when_no_segments(self) -> None:
        assert format_segments_as_dialogue([]) == ""

    def test_formats_single_segment(self) -> None:
        segments = [
            DiarizedTranscriptionSegment(
                id=1, speaker="Speaker A", text="Hello world", start=0.0, end=1.0
            )
        ]

        assert format_segments_as_dialogue(segments) == "Speaker A: Hello world"

    def test_keeps_special_characters(self) -> None:
        segments = [
            DiarizedTranscriptionSegment(
                id=1,
                speaker="Speaker A",
                text="Hello! How's it going? \n New line test. $°",
                start=1.0,
                end=2.0,
            )
        ]

        assert (
            format_segments_as_dialogue(segments)
            == "Speaker A: Hello! How's it going? \n New line test. $°"
        )


class TestDetectNameLosses:
    def test_detects_name_set_to_null(self) -> None:
        previous = [_participant("LOCUTEUR_01", "Alice")]
        current = [_participant("LOCUTEUR_01", None)]

        losses = detect_name_losses(previous, current, step_index=2)

        assert len(losses) == 1
        assert losses[0].reason == "name_set_to_null"
        assert losses[0].speaker_id == "LOCUTEUR_01"
        assert losses[0].previous_name == "Alice"
        assert losses[0].step_index == 2

    def test_detects_disappeared(self) -> None:
        previous = [_participant("LOCUTEUR_01", "Alice")]

        losses = detect_name_losses(previous, [], step_index=3)

        assert len(losses) == 1
        assert losses[0].reason == "disappeared"

    def test_no_loss_when_name_preserved(self) -> None:
        previous = [_participant("LOCUTEUR_01", "Alice")]
        current = [_participant("LOCUTEUR_01", "Alice")]

        assert detect_name_losses(previous, current, step_index=1) == []

    def test_no_loss_when_previous_name_already_none(self) -> None:
        previous = [_participant("LOCUTEUR_01", None)]

        assert detect_name_losses(previous, [], step_index=1) == []

    def test_no_loss_for_newly_added_participant(self) -> None:
        current = [_participant("LOCUTEUR_01", "Alice")]

        assert detect_name_losses([], current, step_index=1) == []

    def test_reports_each_affected_participant(self) -> None:
        previous = [
            _participant("LOCUTEUR_01", "Alice"),
            _participant("LOCUTEUR_02", "Bob"),
            _participant("LOCUTEUR_03", "Charlie"),
        ]
        current = [
            _participant("LOCUTEUR_01", "Alice"),
            _participant("LOCUTEUR_02", None),
        ]

        losses = detect_name_losses(previous, current, step_index=4)

        reasons_by_speaker = {loss.speaker_id: loss.reason for loss in losses}
        assert reasons_by_speaker == {
            "LOCUTEUR_02": "name_set_to_null",
            "LOCUTEUR_03": "disappeared",
        }
