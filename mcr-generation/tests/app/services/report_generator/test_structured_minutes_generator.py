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
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.sections.structured_minutes.types import MinutesContent
from mcr_generation.app.services.utils.input_chunker import Chunk

# Other test modules replace the report_generator package (and sibling modules)
# in sys.modules with MagicMocks. Evict them and re-import so both the factory
# and the generator class resolve to the same real objects.
sys.modules.pop("mcr_generation.app.services.report_generator", None)
sys.modules.pop(
    "mcr_generation.app.services.report_generator.structured_minutes_generator", None
)

_rg_package = importlib.import_module("mcr_generation.app.services.report_generator")
create_report_generator = _rg_package.create_report_generator

_smg_module = importlib.import_module(
    "mcr_generation.app.services.report_generator.structured_minutes_generator"
)
StructuredMinutesGenerator = _smg_module.StructuredMinutesGenerator


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
def mock_theme() -> MinuteTheme:
    return MinuteTheme(
        title="Budget Q1",
        summary="Discussion sur le budget.",
        decisions=[
            MinuteDecision(item="Valider le budget", owner="Alice", due="15/03")
        ],
    )


@pytest.fixture
def mock_content(mock_theme: MinuteTheme) -> MagicMock:
    content = MagicMock()
    content.themes = [mock_theme]
    return content


@pytest.fixture
def mock_synthesis() -> MagicMock:
    synthesis = MagicMock()
    synthesis.open_points = ["Trancher le périmètre du MVP."]
    synthesis.recommendations = ["Planifier un point budget mensuel."]
    return synthesis


class TestFactory:
    def test_factory_returns_structured_minutes_generator(self) -> None:
        generator = create_report_generator(ReportTypes.STRUCTURED_MINUTES)
        assert isinstance(generator, StructuredMinutesGenerator)


class TestStructuredMinutesGeneratorGenerate:
    def test_returns_structured_minutes_instance(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
        mock_synthesis: MagicMock,
    ) -> None:
        with (
            patch.object(
                StructuredMinutesGenerator, "_extract_notes", return_value=None
            ),
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )
            mock_synth_cls.return_value.synthesize.return_value = mock_synthesis

            result = StructuredMinutesGenerator().generate(chunks)

        assert isinstance(result, StructuredMinutes)
        assert result.header == mock_header
        assert result.themes == mock_content.themes
        assert result.open_points == mock_synthesis.open_points
        assert result.recommendations == mock_synthesis.recommendations

    def test_map_reduce_called_with_notes_minutes_hint(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
        mock_synthesis: MagicMock,
    ) -> None:
        minutes_hint = MinutesContent(
            themes=[MinuteTheme(title="SSO", summary=None, decisions=[])]
        )
        extracted = ExtractedNotes(minutes=minutes_hint)

        with (
            patch.object(
                StructuredMinutesGenerator, "_extract_notes", return_value=extracted
            ),
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )
            mock_synth_cls.return_value.synthesize.return_value = mock_synthesis

            StructuredMinutesGenerator().generate(chunks, notes_content="des notes")

        mock_map_reduce_cls.assert_called_once_with(
            meeting_subject=mock_header.title,
            participants=mock_header.participants,
        )
        mock_map_reduce_cls.return_value.map_reduce_all_steps.assert_called_once_with(
            chunks, notes_hint=minutes_hint
        )

    def test_synthesizer_called_with_content_themes(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
        mock_synthesis: MagicMock,
    ) -> None:
        with (
            patch.object(
                StructuredMinutesGenerator, "_extract_notes", return_value=None
            ),
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )
            mock_synth_cls.return_value.synthesize.return_value = mock_synthesis

            StructuredMinutesGenerator().generate(chunks)

        mock_synth_cls.return_value.synthesize.assert_called_once_with(
            mock_content.themes
        )

    def test_map_reduce_receives_none_hint_without_notes(
        self,
        chunks: list[Chunk],
        mock_header: Header,
        mock_content: MagicMock,
        mock_synthesis: MagicMock,
    ) -> None:
        with (
            patch.object(
                StructuredMinutesGenerator, "_extract_notes", return_value=None
            ),
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                mock_content
            )
            mock_synth_cls.return_value.synthesize.return_value = mock_synthesis

            StructuredMinutesGenerator().generate(chunks)

        mock_map_reduce_cls.return_value.map_reduce_all_steps.assert_called_once_with(
            chunks, notes_hint=None
        )

    def test_empty_themes_yield_empty_sections(
        self,
        chunks: list[Chunk],
        mock_header: Header,
    ) -> None:
        empty_content = MagicMock()
        empty_content.themes = []
        empty_synthesis = MagicMock()
        empty_synthesis.open_points = []
        empty_synthesis.recommendations = []

        with (
            patch.object(
                StructuredMinutesGenerator, "_extract_notes", return_value=None
            ),
            patch.object(
                StructuredMinutesGenerator, "generate_header", return_value=mock_header
            ),
            patch.object(_smg_module, "MapReduceMinutes") as mock_map_reduce_cls,
            patch.object(_smg_module, "MinutesSynthesizer") as mock_synth_cls,
        ):
            mock_map_reduce_cls.return_value.map_reduce_all_steps.return_value = (
                empty_content
            )
            mock_synth_cls.return_value.synthesize.return_value = empty_synthesis

            result = StructuredMinutesGenerator().generate(chunks)

        assert result.themes == []
        assert result.open_points == []
        assert result.recommendations == []
