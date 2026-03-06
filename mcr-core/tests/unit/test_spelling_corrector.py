from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector import (
    SpellingCorrector,
)
from mcr_meeting.app.services.llm_post_processing import Chunk


def make_segment(
    id: int, text: str, speaker: str = "Speaker_0"
) -> DiarizedTranscriptionSegment:
    return DiarizedTranscriptionSegment(
        id=id, speaker=speaker, text=text, start=float(id), end=float(id + 1)
    )


@pytest.fixture
def corrector() -> SpellingCorrector:
    with (
        patch("mcr_meeting.app.services.llm_post_processing.LLMSettings"),
        patch("mcr_meeting.app.services.llm_post_processing.OpenAI"),
        patch("mcr_meeting.app.services.llm_post_processing.instructor"),
    ):
        return SpellingCorrector()


class TestSpellingCorrectorCorrect:
    """Tests for SpellingCorrector.correct()."""

    def test_should_return_empty_list_when_no_segments(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that correct([]) returns [] and emits a warning."""
        result = corrector.correct([])

        assert result == []

    def test_should_not_mutate_input_segments(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that the original segment objects are not modified."""
        original_text = "Je suis allez au magasin."
        segment = make_segment(id=0, text=original_text)

        corrector._format_segments_for_llm = MagicMock(  # type: ignore[attr-defined]
            return_value="formatted"
        )
        corrector._chunk_text = MagicMock(  # type: ignore[attr-defined]
            return_value=[Chunk(id=0, text="chunk")]
        )
        corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
            return_value="Je suis allé au magasin."
        )

        corrector.correct([segment])

        assert segment.text == original_text

    def test_should_return_corrected_segments(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that correct() returns new segments with corrected text."""
        segment = make_segment(id=0, text="Je suis allez au magasin.")
        corrected = "Je suis allé au magasin."

        corrector._format_segments_for_llm = MagicMock(  # type: ignore[attr-defined]
            return_value="formatted"
        )
        corrector._chunk_text = MagicMock(  # type: ignore[attr-defined]
            return_value=[Chunk(id=0, text="chunk")]
        )
        corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
            return_value=corrected
        )

        result = corrector.correct([segment])

        assert len(result) == 1
        assert result[0].text == corrected

    def test_should_preserve_segment_metadata(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that speaker, id, start, end are preserved on returned segments."""
        segment = make_segment(id=42, text="Bonjour.", speaker="Alice")

        corrector._format_segments_for_llm = MagicMock(  # type: ignore[attr-defined]
            return_value="formatted"
        )
        corrector._chunk_text = MagicMock(  # type: ignore[attr-defined]
            return_value=[Chunk(id=0, text="chunk")]
        )
        corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
            return_value="Bonjour."
        )

        result = corrector.correct([segment])

        assert result[0].id == 42
        assert result[0].speaker == "Alice"
        assert result[0].start == 42.0
        assert result[0].end == 43.0

    def test_should_correct_each_chunk(self, corrector: SpellingCorrector) -> None:
        """Checks that _correct_chunk is called once per chunk."""
        segments = [
            make_segment(id=0, text="Segment un."),
            make_segment(id=1, text="Segment deux."),
            make_segment(id=2, text="Segment trois."),
        ]

        corrector._format_segments_for_llm = MagicMock(  # type: ignore[attr-defined]
            return_value="formatted"
        )
        corrector._chunk_text = MagicMock(  # type: ignore[attr-defined]
            return_value=[Chunk(id=0, text="chunk-1"), Chunk(id=1, text="chunk-2")]
        )
        corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
            side_effect=[
                "SEGMENT UN.<separator0>",
                "SEGMENT DEUX.<separator1>SEGMENT TROIS.",
            ]
        )

        result = corrector.correct(segments)

        assert corrector._correct_chunk.call_count == 2  # type: ignore[attr-defined]
        assert result[0].text == "SEGMENT UN."
        assert result[1].text == " SEGMENT DEUX."
        assert result[2].text == "SEGMENT TROIS."

    def test_should_return_original_segments_if_split_count_differs(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that original segments are returned when split count mismatches."""
        segments = [
            make_segment(id=0, text="Segment un."),
            make_segment(id=1, text="Segment deux."),
        ]

        corrector._format_segments_for_llm = MagicMock(  # type: ignore[attr-defined]
            return_value="formatted"
        )
        corrector._chunk_text = MagicMock(  # type: ignore[attr-defined]
            return_value=[Chunk(id=0, text="chunk")]
        )
        corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
            return_value="only-one-segment"
        )

        result = corrector.correct(segments)

        assert result == segments


class TestSpellingCorrectorSplitSegments:
    """Tests for SpellingCorrector._split_segments()."""

    def test_should_split_text_on_numeric_separator_markers(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="Segment un.<separator0>"),
            Chunk(id=1, text="Segment deux.<separator1>Segment trois."),
        ]

        result = corrector._split_segments(chunks)

        assert result == ["Segment un.", " Segment deux.", "Segment trois."]

    def test_should_not_split_when_separator_has_no_numeric_id(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="Segment un.<separator>"),
            Chunk(id=1, text="Segment deux."),
        ]

        result = corrector._split_segments(chunks)

        assert result == ["Segment un.<separator> Segment deux."]

    def test_should_keep_leading_empty_segment_when_text_starts_with_separator(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="<separator0>Segment un."),
            Chunk(id=1, text="Segment deux."),
        ]

        result = corrector._split_segments(chunks)

        assert result == ["", "Segment un. Segment deux."]


class TestSpellingCorrectorFormatSegmentsForLlm:
    """Tests for SpellingCorrector._format_segments_for_llm()."""

    def test_should_insert_numeric_separators_starting_at_zero(
        self, corrector: SpellingCorrector
    ) -> None:
        segments = [
            make_segment(id=0, text="Segment un."),
            make_segment(id=1, text="Segment deux."),
            make_segment(id=2, text="Segment trois."),
            make_segment(id=3, text="Segment quatre."),
        ]

        result = corrector._format_segments_for_llm(segments)

        assert "<separator0>" in result
        assert "<separator1>" in result
        assert "<separator2>" in result
        assert "<separator3>" not in result
        assert result.index("<separator0>") < result.index("<separator1>")
        assert result.index("<separator1>") < result.index("<separator2>")

    def test_should_strip_segments_and_keep_last_segment_without_separator(
        self, corrector: SpellingCorrector
    ) -> None:
        segments = [
            make_segment(id=0, text="  Bonjour  "),
            make_segment(id=1, text="  Salut  "),
            make_segment(id=2, text="  Au revoir  "),
        ]

        result = corrector._format_segments_for_llm(segments)

        assert result == "Bonjour <separator0>Salut <separator1>Au revoir"
