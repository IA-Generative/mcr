"""
Unit tests for DetailedSynthesisGenerator.
"""

import importlib
import sys
from unittest.mock import patch

import pytest

from mcr_generation.app.schemas.base import (
    DetailedSynthesis,
    Header,
    Participant,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

# test_base_report_generator injects a MagicMock for this module into
# sys.modules as a sibling guard.  Evict it so importlib gives us the real class.
sys.modules.pop(
    "mcr_generation.app.services.report_generator.detailed_synthesis_generator", None
)

_dsg_module = importlib.import_module(
    "mcr_generation.app.services.report_generator.detailed_synthesis_generator"
)
DetailedSynthesisGenerator = _dsg_module.DetailedSynthesisGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chunks() -> list[Chunk]:
    return [Chunk(id=0, text="premier segment"), Chunk(id=1, text="second segment")]


@pytest.fixture
def mock_header() -> Header:
    participant = Participant(
        speaker_id="LOCUTEUR_00",
        name="Alice Martin",
        role="Directrice financière",
        confidence=0.9,
        association_justification=None,
    )
    return Header(
        title="Réunion Budget Q1",
        objective="Valider le budget du premier trimestre",
        participants=[participant],
        next_meeting="15/03/2026 à 10:00",
    )


# ---------------------------------------------------------------------------
# Tests — DetailedSynthesisGenerator.generate
# ---------------------------------------------------------------------------


class TestDetailedSynthesisGeneratorGenerate:
    def test_returns_detailed_synthesis_instance(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        """generate returns a DetailedSynthesis object."""
        with patch.object(
            DetailedSynthesisGenerator, "generate_header", return_value=mock_header
        ):
            result = DetailedSynthesisGenerator().generate(chunks)

        assert isinstance(result, DetailedSynthesis)

    def test_header_is_taken_from_generate_header(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        """DetailedSynthesis.header is the Header returned by generate_header."""
        with patch.object(
            DetailedSynthesisGenerator, "generate_header", return_value=mock_header
        ):
            result = DetailedSynthesisGenerator().generate(chunks)

        assert result.header == mock_header

    def test_generate_header_called_once_with_chunks(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        """generate_header is called exactly once with the provided chunks."""
        with patch.object(
            DetailedSynthesisGenerator, "generate_header", return_value=mock_header
        ) as mock_generate_header:
            DetailedSynthesisGenerator().generate(chunks)

        mock_generate_header.assert_called_once_with(chunks)

    def test_empty_chunks_are_forwarded(
        self,
        mock_header: Header,
    ) -> None:
        """generate forwards an empty chunk list to generate_header."""
        empty: list[Chunk] = []
        with patch.object(
            DetailedSynthesisGenerator, "generate_header", return_value=mock_header
        ) as mock_generate_header:
            DetailedSynthesisGenerator().generate(empty)

        mock_generate_header.assert_called_once_with(empty)
