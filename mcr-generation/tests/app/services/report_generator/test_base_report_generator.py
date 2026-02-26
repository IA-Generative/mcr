"""
Unit tests for BaseReportGenerator.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcr_generation.app.schemas.base import BaseReport, Header, Participant
from mcr_generation.app.services.utils.input_chunker import Chunk

# Mock the sibling so __init__.py can import it without executing its body.
sys.modules[
    "mcr_generation.app.services.report_generator.decision_record_generator"
] = MagicMock()

# Keep a stable reference to the REAL module so that patch.object targets the
# right object even if sys.modules entry is later replaced by another test file
# (e.g. test_report_generation_task_service.py mocks the whole package).
_base_rg_module = importlib.import_module(
    "mcr_generation.app.services.report_generator.base_report_generator"
)
BaseReportGenerator = _base_rg_module.BaseReportGenerator


class ConcreteReportGenerator(BaseReportGenerator):
    """Minimal concrete subclass used to exercise the abstract base class."""

    def generate(self, chunks: list[Chunk]) -> BaseReport:
        return BaseReport(header=self.generate_header(chunks))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chunks() -> list[Chunk]:
    return [Chunk(id=0, text="premier segment"), Chunk(id=1, text="second segment")]


@pytest.fixture
def mock_intent() -> MagicMock:
    intent = MagicMock()
    intent.title = "Réunion Budget Q1"
    intent.objective = "Valider le budget du premier trimestre"
    return intent


@pytest.fixture
def mock_participants() -> MagicMock:
    participant = Participant(
        speaker_id="LOCUTEUR_00",
        name="Alice Martin",
        role="Directrice financière",
        confidence=0.9,
        association_justification=None,
    )
    participants = MagicMock()
    participants.participants = [participant]
    return participants


@pytest.fixture
def mock_next_meeting() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_refiners(
    mock_refine_intent_cls: MagicMock,
    mock_refine_participants_cls: MagicMock,
    mock_refine_next_meeting_cls: MagicMock,
    mock_intent: MagicMock,
    mock_participants: MagicMock,
    mock_next_meeting: MagicMock,
) -> None:
    mock_refine_intent_cls.return_value.init_then_refine.return_value = mock_intent
    mock_refine_participants_cls.return_value.init_then_refine.return_value = (
        mock_participants
    )
    mock_refine_next_meeting_cls.return_value.init_then_refine.return_value = (
        mock_next_meeting
    )


# ---------------------------------------------------------------------------
# Tests — BaseReportGenerator.generate_header
# ---------------------------------------------------------------------------


class TestGenerateHeader:
    def test_returns_correct_header_instance(
        self,
        chunks: list[Chunk],
        mock_intent: MagicMock,
        mock_participants: MagicMock,
        mock_next_meeting: MagicMock,
    ) -> None:
        """Header fields are populated from the RefineIntent and RefineParticipants outputs."""
        formatted = "Revue backlog\nDate prévue: 15/03/2026"

        with (
            patch.object(_base_rg_module, "RefineIntent") as mock_refine_intent_cls,
            patch.object(
                _base_rg_module, "RefineParticipants"
            ) as mock_refine_participants_cls,
            patch.object(
                _base_rg_module, "RefineNextMeeting"
            ) as mock_refine_next_meeting_cls,
            patch.object(
                _base_rg_module,
                "format_next_meeting_for_report",
                return_value=formatted,
            ),
        ):
            _patch_refiners(
                mock_refine_intent_cls,
                mock_refine_participants_cls,
                mock_refine_next_meeting_cls,
                mock_intent,
                mock_participants,
                mock_next_meeting,
            )

            header = ConcreteReportGenerator().generate_header(chunks)

        assert isinstance(header, Header)
        assert header.title == "Réunion Budget Q1"
        assert header.objective == "Valider le budget du premier trimestre"
        assert header.participants == mock_participants.participants
        assert header.next_meeting == formatted

    def test_next_meeting_is_none_when_formatter_returns_none(
        self,
        chunks: list[Chunk],
        mock_intent: MagicMock,
        mock_participants: MagicMock,
        mock_next_meeting: MagicMock,
    ) -> None:
        """When format_next_meeting_for_report returns None, next_meeting is None."""
        with (
            patch.object(_base_rg_module, "RefineIntent") as mock_refine_intent_cls,
            patch.object(
                _base_rg_module, "RefineParticipants"
            ) as mock_refine_participants_cls,
            patch.object(
                _base_rg_module, "RefineNextMeeting"
            ) as mock_refine_next_meeting_cls,
            patch.object(
                _base_rg_module, "format_next_meeting_for_report", return_value=None
            ),
        ):
            _patch_refiners(
                mock_refine_intent_cls,
                mock_refine_participants_cls,
                mock_refine_next_meeting_cls,
                mock_intent,
                mock_participants,
                mock_next_meeting,
            )

            header = ConcreteReportGenerator().generate_header(chunks)

        assert header.next_meeting is None

    def test_each_refiner_is_called_once_with_chunks(
        self,
        chunks: list[Chunk],
        mock_intent: MagicMock,
        mock_participants: MagicMock,
        mock_next_meeting: MagicMock,
    ) -> None:
        """Each refiner's init_then_refine is called exactly once with the provided chunks."""
        with (
            patch.object(_base_rg_module, "RefineIntent") as mock_refine_intent_cls,
            patch.object(
                _base_rg_module, "RefineParticipants"
            ) as mock_refine_participants_cls,
            patch.object(
                _base_rg_module, "RefineNextMeeting"
            ) as mock_refine_next_meeting_cls,
            patch.object(
                _base_rg_module, "format_next_meeting_for_report", return_value=None
            ),
        ):
            _patch_refiners(
                mock_refine_intent_cls,
                mock_refine_participants_cls,
                mock_refine_next_meeting_cls,
                mock_intent,
                mock_participants,
                mock_next_meeting,
            )

            ConcreteReportGenerator().generate_header(chunks)

        mock_refine_intent_cls.return_value.init_then_refine.assert_called_once_with(
            chunks
        )
        mock_refine_participants_cls.return_value.init_then_refine.assert_called_once_with(
            chunks
        )
        mock_refine_next_meeting_cls.return_value.init_then_refine.assert_called_once_with(
            chunks
        )

    def test_format_next_meeting_is_called_with_next_meeting_result(
        self,
        chunks: list[Chunk],
        mock_intent: MagicMock,
        mock_participants: MagicMock,
        mock_next_meeting: MagicMock,
    ) -> None:
        """format_next_meeting_for_report receives the output of RefineNextMeeting."""
        with (
            patch.object(_base_rg_module, "RefineIntent") as mock_refine_intent_cls,
            patch.object(
                _base_rg_module, "RefineParticipants"
            ) as mock_refine_participants_cls,
            patch.object(
                _base_rg_module, "RefineNextMeeting"
            ) as mock_refine_next_meeting_cls,
            patch.object(
                _base_rg_module, "format_next_meeting_for_report", return_value=None
            ) as mock_format,
        ):
            _patch_refiners(
                mock_refine_intent_cls,
                mock_refine_participants_cls,
                mock_refine_next_meeting_cls,
                mock_intent,
                mock_participants,
                mock_next_meeting,
            )

            ConcreteReportGenerator().generate_header(chunks)

        mock_format.assert_called_once_with(mock_next_meeting)

    def test_empty_participants_list_is_preserved(
        self,
        chunks: list[Chunk],
        mock_intent: MagicMock,
        mock_next_meeting: MagicMock,
    ) -> None:
        """When no participant is identified, participants list is empty."""
        mock_participants = MagicMock()
        mock_participants.participants = []

        with (
            patch.object(_base_rg_module, "RefineIntent") as mock_refine_intent_cls,
            patch.object(
                _base_rg_module, "RefineParticipants"
            ) as mock_refine_participants_cls,
            patch.object(
                _base_rg_module, "RefineNextMeeting"
            ) as mock_refine_next_meeting_cls,
            patch.object(
                _base_rg_module, "format_next_meeting_for_report", return_value=None
            ),
        ):
            _patch_refiners(
                mock_refine_intent_cls,
                mock_refine_participants_cls,
                mock_refine_next_meeting_cls,
                mock_intent,
                mock_participants,
                mock_next_meeting,
            )

            header = ConcreteReportGenerator().generate_header(chunks)

        assert header.participants == []


# ---------------------------------------------------------------------------
# Tests — Abstract interface
# ---------------------------------------------------------------------------


class TestBaseReportGeneratorAbstract:
    def test_cannot_instantiate_directly(self) -> None:
        """BaseReportGenerator cannot be instantiated because generate is abstract."""
        with pytest.raises(TypeError):
            BaseReportGenerator()  # type: ignore[abstract]
