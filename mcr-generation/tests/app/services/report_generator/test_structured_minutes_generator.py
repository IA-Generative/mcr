"""
Unit tests for StructuredMinutesGenerator.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcr_generation.app.schemas.base import (
    Header,
    MinuteDecision,
    MinuteTheme,
    Participant,
    StructuredMinutes,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

# test_base_report_generator injects a MagicMock for this module into
# sys.modules as a sibling guard.  Evict it so importlib gives us the real class.
sys.modules.pop(
    "mcr_generation.app.services.report_generator.structured_minutes_generator", None
)

_smg_module = importlib.import_module(
    "mcr_generation.app.services.report_generator.structured_minutes_generator"
)
StructuredMinutesGenerator = _smg_module.StructuredMinutesGenerator


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
    )
    return Header(
        title="Réunion Budget Q1",
        objective="Valider le budget du premier trimestre",
        participants=[participant],
        next_meeting="15/03/2026 à 10:00",
    )


@pytest.fixture
def mock_themes() -> list[MinuteTheme]:
    return [
        MinuteTheme(
            title="Budget Q1",
            summary="Discussion sur l'enveloppe du trimestre.",
            decisions=[
                MinuteDecision(
                    item="Valider le budget",
                    owner="Alice",
                    due="vendredi",
                )
            ],
        )
    ]


# ---------------------------------------------------------------------------
# Tests — StructuredMinutesGenerator.generate
# ---------------------------------------------------------------------------


class TestStructuredMinutesGeneratorGenerate:
    def test_returns_structured_minutes_instance(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_themes: list[MinuteTheme],
    ) -> None:
        with (
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            content = MagicMock()
            content.themes = mock_themes
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = content
            synth = MagicMock()
            synth.open_points = ["Question X non tranchée"]
            synth.recommendations = ["Planifier un suivi"]
            mock_synth_cls.return_value.synthesize.return_value = synth

            result = StructuredMinutesGenerator().generate(chunks)

        assert isinstance(result, StructuredMinutes)
        assert result.header == mock_header
        assert result.themes == mock_themes
        assert result.open_points == ["Question X non tranchée"]
        assert result.recommendations == ["Planifier un suivi"]

    def test_map_reduce_and_synthesizer_wired_with_header(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_themes: list[MinuteTheme],
    ) -> None:
        with (
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ) as mock_generate_header,
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            content = MagicMock()
            content.themes = mock_themes
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = content
            synth = MagicMock()
            synth.open_points = []
            synth.recommendations = []
            mock_synth_cls.return_value.synthesize.return_value = synth

            StructuredMinutesGenerator().generate(chunks)

        mock_generate_header.assert_called_once_with(chunks, extracted_notes=None)
        mock_map_reduce_cls.assert_called_once_with(
            meeting_subject=mock_header.title,
            participants=mock_header.participants,
        )
        mock_map_reduce_cls.return_value.map_reduce_all_steps.assert_called_once_with(
            chunks
        )
        mock_synth_cls.assert_called_once_with(
            meeting_subject=mock_header.title,
            participants=mock_header.participants,
        )
        mock_synth_cls.return_value.synthesize.assert_called_once_with(mock_themes)

    def test_empty_themes_yields_empty_sections(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        with (
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            content = MagicMock()
            content.themes = []
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = content
            synth = MagicMock()
            synth.open_points = []
            synth.recommendations = []
            mock_synth_cls.return_value.synthesize.return_value = synth

            result = StructuredMinutesGenerator().generate(chunks)

        assert result.themes == []
        assert result.open_points == []
        assert result.recommendations == []
