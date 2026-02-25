from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector import (
    SpellingCorrector,
)


def make_segment(
    id: int, text: str, speaker: str = "Speaker_0"
) -> DiarizedTranscriptionSegment:
    return DiarizedTranscriptionSegment(
        id=id, speaker=speaker, text=text, start=float(id), end=float(id + 1)
    )


@pytest.fixture
def corrector() -> SpellingCorrector:
    with (
        patch(
            "mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector.LLMSettings"
        ),
        patch(
            "mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector.OpenAI"
        ),
        patch(
            "mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector.instructor"
        ),
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

    def test_should_warn_when_no_segments(self, corrector: SpellingCorrector) -> None:
        """Checks that a warning is logged when segments list is empty."""
        with patch(
            "mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector.logger"
        ) as mock_logger:
            corrector.correct([])

        mock_logger.warning.assert_called_once_with("No segments found to correct")

    def test_should_not_mutate_input_segments(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that the original segment objects are not modified."""
        original_text = "Je suis allez au magasin."
        segment = make_segment(id=0, text=original_text)
        corrector._correct_segment = MagicMock(return_value="Je suis allé au magasin.")  # type: ignore[method-assign]

        corrector.correct([segment])

        assert segment.text == original_text

    def test_should_return_corrected_segments(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that correct() returns new segments with corrected text."""
        segment = make_segment(id=0, text="Je suis allez au magasin.")
        corrected = "Je suis allé au magasin."
        corrector._correct_segment = MagicMock(return_value=corrected)  # type: ignore[method-assign]

        result = corrector.correct([segment])

        assert len(result) == 1
        assert result[0].text == corrected

    def test_should_preserve_segment_metadata(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that speaker, id, start, end are preserved on returned segments."""
        segment = make_segment(id=42, text="Bonjour.", speaker="Alice")
        corrector._correct_segment = MagicMock(return_value="Bonjour.")  # type: ignore[method-assign]

        result = corrector.correct([segment])

        assert result[0].id == 42
        assert result[0].speaker == "Alice"
        assert result[0].start == 42.0
        assert result[0].end == 43.0

    def test_should_correct_each_segment_independently(
        self, corrector: SpellingCorrector
    ) -> None:
        """Checks that _correct_segment is called once per segment."""
        segments = [
            make_segment(id=0, text="Segment un."),
            make_segment(id=1, text="Segment deux."),
            make_segment(id=2, text="Segment trois."),
        ]
        corrector._correct_segment = MagicMock(side_effect=lambda t: t.upper())  # type: ignore[method-assign]

        result = corrector.correct(segments)

        assert corrector._correct_segment.call_count == 3  # type: ignore[attr-defined]
        assert result[0].text == "SEGMENT UN."
        assert result[1].text == "SEGMENT DEUX."
        assert result[2].text == "SEGMENT TROIS."
