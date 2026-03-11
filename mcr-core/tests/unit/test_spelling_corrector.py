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
                "SEGMENT UN.<separator1>",
                "SEGMENT DEUX.<separator2>SEGMENT TROIS.",
            ]
        )

        result = corrector.correct(segments)

        assert corrector._correct_chunk.call_count == 2  # type: ignore[attr-defined]
        assert result[0].text == "SEGMENT UN."
        assert result[1].text == " SEGMENT DEUX."
        assert result[2].text == "SEGMENT TROIS."

    def test_should_replace_only_segments_with_available_corrected_text(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that only mapped segment ids are replaced and missing ids are kept."""
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

        assert result[0].text == "only-one-segment"
        assert result[1].text == "Segment deux."


class TestSpellingCorrectorSplitSegments:
    """Tests for SpellingCorrector._split_segments()."""

    def test_should_map_numeric_separator_markers_to_following_text(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="Segment un.<separator1>"),
            Chunk(id=1, text="Segment deux.<separator2>Segment trois."),
        ]

        result = corrector._split_segments(chunks=chunks, expected_segments_count=3)

        assert result == {0: "Segment un.", 1: " Segment deux.", 2: "Segment trois."}

    def test_should_map_missing_separator_ids_to_none(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="Segment un.<separator1>Segment deux."),
            Chunk(id=1, text="Segment trois."),
        ]

        result = corrector._split_segments(chunks=chunks, expected_segments_count=4)

        assert result == {0: "Segment un.", 1: None, 2: None, 3: None}

    def test_should_invalidate_previous_segment_when_separator_missing(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="A<separator1>B<separator3>D"),
        ]

        result = corrector._split_segments(chunks=chunks, expected_segments_count=4)

        assert result == {0: "A", 1: None, 2: None, 3: "D"}

    def test_should_handle_last_separator_id_using_expected_count(
        self, corrector: SpellingCorrector
    ) -> None:
        chunks = [
            Chunk(id=0, text="A<separator1>B<separator2>C<separator3>D"),
        ]

        result = corrector._split_segments(chunks=chunks, expected_segments_count=4)

        assert result == {0: "A", 1: "B", 2: "C", 3: "D"}


class TestSpellingCorrectorFillSegmentTextsFromParts:
    """Tests for SpellingCorrector._fill_segment_texts_from_parts()."""

    def test_should_assign_text_for_each_found_separator_id(
        self, corrector: SpellingCorrector
    ) -> None:
        parts = ["A", "1", "B", "2", "C"]
        segment_texts: dict[int, str | None] = {0: "A", 1: None, 2: None}

        found_separator_ids = corrector._fill_segment_texts_from_parts(
            parts=parts,
            segment_texts=segment_texts,
        )

        assert found_separator_ids == {1, 2}
        assert segment_texts == {0: "A", 1: "B", 2: "C"}


class TestSpellingCorrectorInvalidateMissingSeparators:
    """Tests for SpellingCorrector._invalidate_missing_separators()."""

    def test_should_invalidate_previous_segment_when_one_separator_is_missing(
        self, corrector: SpellingCorrector
    ) -> None:
        segment_texts: dict[int, str | None] = {0: "A", 1: "B", 2: None, 3: "D"}

        corrector._invalidate_missing_separators(
            found_separator_ids={1, 3},
            segment_texts=segment_texts,
            expected_segments_count=4,
        )

        assert segment_texts == {0: "A", 1: None, 2: None, 3: "D"}

    def test_should_only_invalidate_missing_separator_when_first_separator_missing(
        self, corrector: SpellingCorrector
    ) -> None:
        segment_texts: dict[int, str | None] = {0: "A", 1: "B", 2: "C"}

        corrector._invalidate_missing_separators(
            found_separator_ids={2},
            segment_texts=segment_texts,
            expected_segments_count=3,
        )

        assert segment_texts == {0: "A", 1: None, 2: "C"}


class TestSpellingCorrectorReplaceCorrectedSegments:
    """Tests for SpellingCorrector._replace_corrected_segments()."""

    def test_should_replace_only_segments_with_non_none_corrected_text(
        self, corrector: SpellingCorrector
    ) -> None:
        segments = [
            make_segment(id=0, text="Original 0", speaker="Alice"),
            make_segment(id=1, text="Original 1", speaker="Bob"),
            make_segment(id=2, text="Original 2", speaker="Carol"),
        ]
        segment_texts: dict[int, str | None] = {
            0: "Corrected 0",
            1: None,
            2: "Corrected 2",
        }

        result = corrector._replace_corrected_segments(segments, segment_texts)

        assert [segment.text for segment in result] == [
            "Corrected 0",
            "Original 1",
            "Corrected 2",
        ]

    def test_should_keep_original_segment_instance_when_text_is_none(
        self, corrector: SpellingCorrector
    ) -> None:
        segments = [
            make_segment(id=0, text="Original 0"),
            make_segment(id=1, text="Original 1"),
        ]
        segment_texts: dict[int, str | None] = {0: "Corrected 0", 1: None}

        result = corrector._replace_corrected_segments(segments, segment_texts)

        assert result[0] is not segments[0]
        assert result[1] is segments[1]


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

        assert "<separator1>" in result
        assert "<separator2>" in result
        assert "<separator3>" in result
        assert "<separator4>" not in result
        assert result.index("<separator1>") < result.index("<separator2>")
        assert result.index("<separator2>") < result.index("<separator3>")

    def test_should_strip_segments_and_keep_last_segment_without_separator(
        self, corrector: SpellingCorrector
    ) -> None:
        segments = [
            make_segment(id=0, text="  Bonjour  "),
            make_segment(id=1, text="  Salut  "),
            make_segment(id=2, text="  Au revoir  "),
        ]

        result = corrector._format_segments_for_llm(segments)

        assert result == "Bonjour <separator1>Salut <separator2>Au revoir"
