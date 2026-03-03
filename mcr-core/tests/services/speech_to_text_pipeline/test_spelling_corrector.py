from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector import (
    SpellingCorrector,
)
from mcr_meeting.app.services.llm_post_processing import Chunk


def make_segment(
    segment_id: int, text: str, speaker: str = "Speaker_0"
) -> DiarizedTranscriptionSegment:
    return DiarizedTranscriptionSegment(
        id=segment_id,
        speaker=speaker,
        text=text,
        start=float(segment_id),
        end=float(segment_id + 1),
    )


@pytest.fixture
def corrector() -> SpellingCorrector:
    with (
        patch("mcr_meeting.app.services.llm_post_processing.LLMSettings"),
        patch("mcr_meeting.app.services.llm_post_processing.OpenAI"),
        patch("mcr_meeting.app.services.llm_post_processing.instructor"),
    ):
        return SpellingCorrector()


def test_correct_returns_empty_list_when_no_segments(
    corrector: SpellingCorrector,
) -> None:
    result = corrector.correct([])

    assert result == []


def test_correct_returns_corrected_segments_and_preserves_metadata(
    corrector: SpellingCorrector,
) -> None:
    segments = [
        make_segment(segment_id=0, text="Je suis allez au magasin.", speaker="Alice"),
        make_segment(segment_id=1, text="On vas partir.", speaker="Bob"),
    ]

    corrector._format_segments_for_llm = MagicMock(return_value="formatted")  # type: ignore[attr-defined]
    corrector._chunk_text = MagicMock(return_value=[Chunk(id=0, text="chunk")])  # type: ignore[attr-defined]
    corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
        return_value="Je suis allé au magasin.<separator>On va partir."
    )

    result = corrector.correct(segments)

    assert [segment.text for segment in result] == [
        "Je suis allé au magasin.",
        "On va partir.",
    ]
    assert result[0].speaker == "Alice"
    assert result[1].speaker == "Bob"
    assert result[0].id == 0
    assert result[1].id == 1


def test_correct_returns_original_segments_when_split_count_mismatches(
    corrector: SpellingCorrector,
) -> None:
    segments = [
        make_segment(segment_id=0, text="Segment un."),
        make_segment(segment_id=1, text="Segment deux."),
    ]

    corrector._format_segments_for_llm = MagicMock(return_value="formatted")  # type: ignore[attr-defined]
    corrector._chunk_text = MagicMock(return_value=[Chunk(id=0, text="chunk")])  # type: ignore[attr-defined]
    corrector._correct_chunk = MagicMock(return_value="Only one segment")  # type: ignore[attr-defined]

    result = corrector.correct(segments)

    assert result == segments


def test_correct_calls_correct_chunk_once_per_chunk(
    corrector: SpellingCorrector,
) -> None:
    segments = [
        make_segment(segment_id=0, text="Segment un."),
        make_segment(segment_id=1, text="Segment deux."),
        make_segment(segment_id=2, text="Segment trois."),
    ]

    corrector._format_segments_for_llm = MagicMock(return_value="formatted")  # type: ignore[attr-defined]
    corrector._chunk_text = MagicMock(  # type: ignore[attr-defined]
        return_value=[Chunk(id=0, text="chunk-1"), Chunk(id=1, text="chunk-2")]
    )
    corrector._correct_chunk = MagicMock(  # type: ignore[attr-defined]
        side_effect=[
            "SEGMENT UN.<separator>",
            "SEGMENT DEUX.<separator>SEGMENT TROIS.",
        ]
    )

    result = corrector.correct(segments)

    assert corrector._correct_chunk.call_count == 2  # type: ignore[attr-defined]
    assert [segment.text for segment in result] == [
        "SEGMENT UN.",
        "SEGMENT DEUX.",
        "SEGMENT TROIS.",
    ]
