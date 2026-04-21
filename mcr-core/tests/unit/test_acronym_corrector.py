from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_acronyms.acronym_corrector import (
    AcronymCorrector,
)
from mcr_meeting.app.services.llm_post_processing import Chunk


def make_segment(
    id: int, text: str, speaker: str = "Speaker_0"
) -> DiarizedTranscriptionSegment:
    return DiarizedTranscriptionSegment(
        id=id, speaker=speaker, text=text, start=float(id), end=float(id + 1)
    )


@pytest.fixture
def corrector() -> AcronymCorrector:
    with (
        patch("mcr_meeting.app.services.llm_post_processing.LLMSettings"),
        patch("mcr_meeting.app.services.llm_post_processing.OpenAI"),
        patch("mcr_meeting.app.services.llm_post_processing.instructor"),
    ):
        return AcronymCorrector()


class TestAcronymCorrectorCorrect:
    def test_should_return_empty_list_when_no_segments(
        self, corrector: AcronymCorrector
    ) -> None:
        result = corrector.correct([])
        assert result == []

    def test_should_not_mutate_input_segments(
        self, corrector: AcronymCorrector
    ) -> None:
        original_text = "La ance a délivré les titres."
        segment = make_segment(id=0, text=original_text)

        corrector._format_segments_for_llm = MagicMock(return_value="formatted")
        corrector._chunk_text = MagicMock(return_value=[Chunk(id=0, text="chunk")])
        corrector._correct_chunk = MagicMock(
            return_value="La ANTS a délivré les titres."
        )

        corrector.correct([segment])

        assert segment.text == original_text

    def test_should_preserve_segment_metadata(
        self, corrector: AcronymCorrector
    ) -> None:
        segment = make_segment(id=42, text="Bonjour.", speaker="Alice")

        corrector._format_segments_for_llm = MagicMock(return_value="formatted")
        corrector._chunk_text = MagicMock(return_value=[Chunk(id=0, text="chunk")])
        corrector._correct_chunk = MagicMock(return_value="Bonjour.")

        result = corrector.correct([segment])

        assert result[0].id == 42
        assert result[0].speaker == "Alice"
        assert result[0].start == 42.0
        assert result[0].end == 43.0


class TestAcronymCorrectorCorrectChunk:
    def test_correct_chunk_uses_acronym_prompt_with_glossary(
        self, corrector: AcronymCorrector
    ) -> None:
        chunk = Chunk(id=0, text="La ance a délivré les titres.")

        mock_create = MagicMock()
        mock_create.corrected_text = "La ANTS a délivré les titres."
        corrector.client.chat.completions.create = MagicMock(return_value=mock_create)

        result = corrector._correct_chunk(chunk)

        call_args = corrector.client.chat.completions.create.call_args
        prompt_content = call_args.kwargs["messages"][0]["content"]

        assert "ANTS" in prompt_content
        assert "DGPN" in prompt_content
        assert (
            "acronymes" in prompt_content.lower() or "sigles" in prompt_content.lower()
        )
        assert result == "La ANTS a délivré les titres."
