from mcr_meeting.app.domain.transcription.text_chunking import (
    format_segments_for_llm,
    reassemble_corrected_segments,
)
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


def _segment(
    id: int, text: str, speaker: str = "Speaker_0"
) -> DiarizedTranscriptionSegment:
    return DiarizedTranscriptionSegment(
        id=id, speaker=speaker, text=text, start=float(id), end=float(id + 1)
    )


class TestFormatSegmentsForLLM:
    def test_returns_empty_string_for_no_segments(self) -> None:
        assert format_segments_for_llm([]) == ""

    def test_inserts_numeric_separators_and_keeps_last_without_one(self) -> None:
        segments = [
            _segment(0, "  first  "),
            _segment(1, "second"),
            _segment(2, "third"),
        ]

        result = format_segments_for_llm(segments)

        assert result == "first <separator1>second <separator2>third"


class TestReassembleCorrectedSegments:
    def test_round_trip_identity_preserves_segment_texts(self) -> None:
        segments = [_segment(0, "first"), _segment(1, "second"), _segment(2, "third")]
        corrected = [format_segments_for_llm(segments)]

        result = reassemble_corrected_segments(corrected, segments)

        assert [s.text.strip() for s in result] == ["first", "second", "third"]

    def test_preserves_metadata(self) -> None:
        segments = [_segment(42, "hello", speaker="Alice")]

        result = reassemble_corrected_segments(["hello"], segments)

        assert result[0].id == 42
        assert result[0].speaker == "Alice"
        assert result[0].start == 42.0
        assert result[0].end == 43.0

    def test_missing_separator_keeps_original_text_and_invalidates_previous(
        self,
    ) -> None:
        segments = [_segment(0, "a"), _segment(1, "b"), _segment(2, "c")]
        # separator2 dropped by the LLM: segment 1 and 2 fall back to originals
        corrected = ["A <separator1>B C"]

        result = reassemble_corrected_segments(corrected, segments)

        assert result[1].text == "b"
        assert result[2].text == "c"
