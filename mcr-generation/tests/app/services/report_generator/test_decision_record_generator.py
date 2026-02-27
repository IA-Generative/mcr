"""
Unit tests for DecisionRecordGenerator.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcr_generation.app.schemas.base import (
    DecisionRecord,
    Header,
    Participant,
    Topic,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

# test_base_report_generator injects a MagicMock for this module into
# sys.modules as a sibling guard.  Evict it so importlib gives us the real class.
sys.modules.pop(
    "mcr_generation.app.services.report_generator.decision_record_generator", None
)

_drg_module = importlib.import_module(
    "mcr_generation.app.services.report_generator.decision_record_generator"
)
DecisionRecordGenerator = _drg_module.DecisionRecordGenerator


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


@pytest.fixture
def mock_content() -> MagicMock:
    topic = Topic(
        title="Budget Q1",
        introduction_text="Discussion sur le budget.",
        details=["Enveloppe de 50 k€."],
        main_decision="Alice a décidé de valider le budget.",
    )
    content = MagicMock()
    content.topics = [topic]
    content.next_steps = ["Envoyer le compte-rendu avant vendredi."]
    return content


# ---------------------------------------------------------------------------
# Tests — DecisionRecordGenerator.generate
# ---------------------------------------------------------------------------


class TestDecisionRecordGeneratorGenerate:
    def test_returns_decision_record_instance(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """generate returns a DecisionRecord object."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            result = DecisionRecordGenerator().generate(chunks)

        assert isinstance(result, DecisionRecord)

    def test_header_is_taken_from_generate_header(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """DecisionRecord.header is the Header returned by generate_header."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            result = DecisionRecordGenerator().generate(chunks)

        assert result.header == mock_header

    def test_topics_with_decision_come_from_map_reduce(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """topics_with_decision is populated from content.topics."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            result = DecisionRecordGenerator().generate(chunks)

        assert result.topics_with_decision == mock_content.topics

    def test_next_steps_come_from_map_reduce(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """next_steps is populated from content.next_steps."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            result = DecisionRecordGenerator().generate(chunks)

        assert result.next_steps == mock_content.next_steps

    def test_map_reduce_topics_instantiated_with_header_title_and_participants(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """MapReduceTopics is instantiated with meeting_subject=header.title and
        speaker_mapping wrapping header.participants."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            DecisionRecordGenerator().generate(chunks)

        mock_map_reduce_cls.assert_called_once_with(
            meeting_subject=mock_header.title,
            participants=mock_header.participants,
        )

    def test_map_reduce_all_steps_called_once_with_chunks(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """map_reduce_all_steps is called exactly once with the provided chunks."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            DecisionRecordGenerator().generate(chunks)

        mock_map_reduce_cls.return_value.map_reduce_all_steps.assert_called_once_with(
            chunks
        )

    def test_generate_header_called_once_with_chunks(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """generate_header is called exactly once with the provided chunks."""
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ) as mock_generate_header,
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            DecisionRecordGenerator().generate(chunks)

        mock_generate_header.assert_called_once_with(chunks)

    def test_empty_chunks_are_forwarded(
        self,
        mock_header: Header,
        mock_content: MagicMock,
    ) -> None:
        """generate forwards an empty chunk list to both generate_header and map_reduce_all_steps."""
        empty: list[Chunk] = []
        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ) as mock_generate_header,
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )

            DecisionRecordGenerator().generate(empty)

        mock_generate_header.assert_called_once_with(empty)
        mock_map_reduce_cls.return_value.map_reduce_all_steps.assert_called_once_with(
            empty
        )

    def test_empty_topics_and_next_steps(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        """generate handles content with no topics and no next steps."""
        empty_content = MagicMock()
        empty_content.topics = []
        empty_content.next_steps = []

        with (
            patch.object(
                DecisionRecordGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_drg_module, "MapReduceTopics") as mock_map_reduce_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                empty_content
            )

            result = DecisionRecordGenerator().generate(chunks)

        assert result.topics_with_decision == []
        assert result.next_steps == []
