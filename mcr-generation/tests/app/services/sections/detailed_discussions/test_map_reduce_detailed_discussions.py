"""Unit tests for MapReduceDetailedDiscussions — notes_hint wiring (US6)."""

import importlib
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mcr_generation.app.schemas.base import DetailedDiscussion
from mcr_generation.app.services.sections.detailed_discussions.types import (
    DiscussionsContent,
    MappedDecision,
    MappedDetailedDiscussion,
)

# conftest.pytest_configure registers a MagicMock for this module; evict it so
# importlib gives us the real MapReduceDetailedDiscussions class.
sys.modules.pop(
    "mcr_generation.app.services.sections.detailed_discussions.map_reduce_detailed_discussions",
    None,
)
_mrd_module = importlib.import_module(
    "mcr_generation.app.services.sections.detailed_discussions.map_reduce_detailed_discussions"
)
MapReduceDetailedDiscussions = _mrd_module.MapReduceDetailedDiscussions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mapped_discussion() -> MappedDetailedDiscussion:
    return MappedDetailedDiscussion(
        topic="Budget Q1",
        topic_confidence=0.9,
        takeaways=[],
        decisions=[
            MappedDecision(
                decision="Alice valide le budget.",
                relevance_score=0.9,
                confidence_score=0.9,
            )
        ],
        chunk_id=0,
    )


@pytest.fixture
def notes_hint() -> DiscussionsContent:
    return DiscussionsContent(
        detailed_discussions=[
            DetailedDiscussion(
                title="Budget Q1",
                key_ideas=["Note humaine: budget validé."],
                decisions=[],
                actions=[],
                focus_points=[],
            )
        ]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _captured_user_message(mock_call: MagicMock) -> str:
    return mock_call.call_args.kwargs["user_message_content"]


class TestNotesSectionInjection:
    """Validates that the notes block appears only when notes_hint is passed."""

    def test_reduce_prompt_omits_notes_section_when_no_hint(
        self, mapped_discussion: MappedDetailedDiscussion
    ) -> None:
        fake_response = DiscussionsContent(detailed_discussions=[])
        with patch.object(
            _mrd_module,
            "call_llm_with_structured_output",
            return_value=fake_response,
        ) as mock_call:
            MapReduceDetailedDiscussions().reduce_discussions_into_content(
                [mapped_discussion], notes_hint=None
            )

        prompt = _captured_user_message(mock_call)
        assert "Notes du rédacteur" not in prompt

    def test_map_reduce_all_steps_with_hint_injects_full_notes_block(
        self,
        mapped_discussion: MappedDetailedDiscussion,
        notes_hint: DiscussionsContent,
    ) -> None:
        """End-to-end via map_reduce_all_steps: confirms the hint is propagated
        and the full notes block (header + JSON + usage rules) lands in the prompt."""
        fake_response = DiscussionsContent(detailed_discussions=[])

        def fake_map(
            self: Any,  # noqa: ANN401
            chunks: Any,  # noqa: ANN401
        ) -> tuple[list[list[MappedDetailedDiscussion]], list[int]]:
            return ([[mapped_discussion]], [])

        with (
            patch.object(
                _mrd_module.MapReduceDetailedDiscussions,
                "_map_chunks_in_parallel",
                fake_map,
            ),
            patch.object(
                _mrd_module,
                "call_llm_with_structured_output",
                return_value=fake_response,
            ) as mock_call,
        ):
            MapReduceDetailedDiscussions().map_reduce_all_steps(
                [], notes_hint=notes_hint
            )

        prompt = _captured_user_message(mock_call)
        assert "## Notes du rédacteur" in prompt
        assert "### Comment utiliser ces notes" in prompt
        assert notes_hint.model_dump_json() in prompt
