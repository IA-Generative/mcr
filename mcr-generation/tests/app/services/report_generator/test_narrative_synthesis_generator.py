"""Unit tests for NarrativeSynthesisGenerator."""

import importlib
import sys
from unittest.mock import patch

import pytest

from mcr_generation.app.schemas.base import NarrativeSynthesis
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.sections.narrative.types import NarrativeChunk
from mcr_generation.app.services.utils.input_chunker import Chunk

# test_base_report_generator injects a MagicMock for this module into
# sys.modules as a sibling guard.  Evict it so importlib gives us the real class.
sys.modules.pop(
    "mcr_generation.app.services.report_generator.narrative_synthesis_generator", None
)

_nsg_module = importlib.import_module(
    "mcr_generation.app.services.report_generator.narrative_synthesis_generator"
)
NarrativeSynthesisGenerator = _nsg_module.NarrativeSynthesisGenerator

_MODULE_PATH = (
    "mcr_generation.app.services.report_generator.narrative_synthesis_generator"
)


@pytest.fixture
def chunks() -> list[Chunk]:
    return [Chunk(id=0, text="premier segment"), Chunk(id=1, text="second segment")]


class TestNarrativeSynthesisGeneratorGenerate:
    def test_concatenates_chunk_narratives(self, chunks: list[Chunk]) -> None:
        """Chaque chunk est reformulé puis concaténé avec un double saut de ligne."""
        with patch(
            f"{_MODULE_PATH}.call_llm_with_structured_output",
            side_effect=[
                NarrativeChunk(narrative="Alice a dit que A."),
                NarrativeChunk(narrative="Bob a répondu que B."),
            ],
        ) as mock_llm:
            result = NarrativeSynthesisGenerator().generate(chunks)

        assert isinstance(result, NarrativeSynthesis)
        assert result.narrative == "Alice a dit que A.\n\nBob a répondu que B."
        assert mock_llm.call_count == 2

    def test_passes_chunk_text_to_prompt(self, chunks: list[Chunk]) -> None:
        """Le texte du chunk est injecté dans le message envoyé au LLM."""
        with patch(
            f"{_MODULE_PATH}.call_llm_with_structured_output",
            side_effect=[
                NarrativeChunk(narrative="x"),
                NarrativeChunk(narrative="y"),
            ],
        ) as mock_llm:
            NarrativeSynthesisGenerator().generate(chunks)

        first_message = mock_llm.call_args_list[0].kwargs["user_message_content"]
        assert "premier segment" in first_message

    def test_empty_chunks_returns_empty_narrative(self) -> None:
        """Sans chunk, aucune reformulation et narratif vide."""
        with patch(f"{_MODULE_PATH}.call_llm_with_structured_output") as mock_llm:
            result = NarrativeSynthesisGenerator().generate([])

        assert isinstance(result, NarrativeSynthesis)
        assert result.narrative == ""
        mock_llm.assert_not_called()

    def test_report_type_is_narrative_synthesis(self) -> None:
        """Le générateur déclare bien son report_type."""
        assert (
            NarrativeSynthesisGenerator.report_type == ReportTypes.NARRATIVE_SYNTHESIS
        )
