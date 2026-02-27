"""
Unit tests for DetailedSynthesisGenerator.
"""

import importlib
import sys
from unittest.mock import patch

import pytest

from mcr_generation.app.schemas.base import (
    DetailedDiscussion,
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
    def test_generate_returns_synthesis_with_header_chunks(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        """generate returns DetailedSynthesis with correct header and empty sections."""
        with (
            patch.object(
                DetailedSynthesisGenerator, "generate_header", return_value=mock_header
            ),
            patch(
                "mcr_generation.app.services.report_generator.detailed_synthesis_generator.MapReduceDetailedDiscussions"
            ) as mock_map_reduce_class,
        ):
            mock_map_reduce = mock_map_reduce_class.return_value
            mock_map_reduce.map_reduce_all_steps.return_value.detailed_discussions = []

            result = DetailedSynthesisGenerator().generate(chunks)

        assert isinstance(result, DetailedSynthesis)
        assert result.header == mock_header
        assert result.discussions_summary == []
        assert result.to_do_list == []
        assert result.to_monitor_list == []

    def test_generate_header_called_with_different_chunk_inputs(
        self,
        mock_header: Header,
    ) -> None:
        """generate_header is called with provided chunks, including empty list."""
        for test_chunks in (
            [Chunk(id=0, text="premier segment"), Chunk(id=1, text="second segment")],
            [],
        ):
            with (
                patch.object(
                    DetailedSynthesisGenerator,
                    "generate_header",
                    return_value=mock_header,
                ) as mock_generate_header,
                patch(
                    "mcr_generation.app.services.report_generator.detailed_synthesis_generator.MapReduceDetailedDiscussions"
                ) as mock_map_reduce_class,
            ):
                mock_map_reduce = mock_map_reduce_class.return_value
                mock_map_reduce.map_reduce_all_steps.return_value.detailed_discussions = []

                DetailedSynthesisGenerator().generate(test_chunks)

            mock_generate_header.assert_called_once_with(test_chunks)

    def test_map_reduce_initialized_and_executed(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        """MapReduceDetailedDiscussions is initialized with header data and
        map_reduce_all_steps is called with chunks."""
        mock_discussion = DetailedDiscussion(
            title="Budget Discussion",
            key_ideas=["Budget planning for Q1"],
            decisions=["Approved Q1 budget"],
            actions=["Send budget document"],
            focus_points=["Monitor spending"],
        )
        mock_discussions = [mock_discussion]

        with (
            patch.object(
                DetailedSynthesisGenerator, "generate_header", return_value=mock_header
            ),
            patch(
                "mcr_generation.app.services.report_generator.detailed_synthesis_generator.MapReduceDetailedDiscussions"
            ) as mock_map_reduce_class,
            patch(
                "mcr_generation.app.services.report_generator.detailed_synthesis_generator.Participants"
            ) as mock_participants_class,
        ):
            mock_map_reduce = mock_map_reduce_class.return_value
            mock_map_reduce.map_reduce_all_steps.return_value.detailed_discussions = (
                mock_discussions
            )
            mock_participants = mock_participants_class.return_value

            result = DetailedSynthesisGenerator().generate(chunks)

        # Verify Participants creation and MapReduceDetailedDiscussions initialization
        mock_participants_class.assert_called_once_with(
            participants=mock_header.participants
        )
        mock_map_reduce_class.assert_called_once_with(
            meeting_subject=mock_header.title,
            speaker_mapping=mock_participants,
        )
        # Verify map_reduce_all_steps execution and result
        mock_map_reduce.map_reduce_all_steps.assert_called_once_with(chunks)
        assert result.detailed_discussions == mock_discussions
