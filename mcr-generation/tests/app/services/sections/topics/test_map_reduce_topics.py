"""Unit tests for MapReduceTopics — notes_hint wiring (US5)."""

import importlib
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mcr_generation.app.schemas.base import Topic
from mcr_generation.app.services.sections.topics.types import (
    MappedDecision,
    MappedTopic,
    MappedTopicDetails,
    TopicsContent,
)

# conftest.pytest_configure registers a MagicMock for this module; evict it so
# importlib gives us the real MapReduceTopics class.
sys.modules.pop("mcr_generation.app.services.sections.topics.map_reduce_topics", None)
_mrt_module = importlib.import_module(
    "mcr_generation.app.services.sections.topics.map_reduce_topics"
)
MapReduceTopics = _mrt_module.MapReduceTopics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mapped_topic() -> MappedTopic:
    return MappedTopic(
        topic="Budget Q1",
        topic_confidence=0.9,
        details=MappedTopicDetails(facts=["Budget de 50 k€."]),
        decisions=[
            MappedDecision(
                decision="Alice valide le budget.",
                decision_confidence=0.9,
            )
        ],
        chunk_id=0,
    )


@pytest.fixture
def notes_hint() -> TopicsContent:
    return TopicsContent(
        topics=[
            Topic(
                title="Budget Q1",
                introduction_text=None,
                details=["Note humaine: budget validé."],
            )
        ],
        next_steps=["Envoyer le CR avant vendredi (note)."],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _captured_user_message(mock_call: MagicMock) -> str:
    return mock_call.call_args.kwargs["user_message_content"]


class TestNotesSectionInjection:
    """Validates that the notes block appears only when notes_hint is passed."""

    def test_reduce_prompt_omits_notes_section_when_no_hint(
        self, mapped_topic: MappedTopic
    ) -> None:
        fake_response = TopicsContent(topics=[], next_steps=[])
        with patch.object(
            _mrt_module,
            "call_llm_with_structured_output",
            return_value=fake_response,
        ) as mock_call:
            MapReduceTopics().reduce_topics_into_content(
                [mapped_topic], notes_hint=None
            )

        prompt = _captured_user_message(mock_call)
        assert "Notes du rédacteur" not in prompt

    def test_map_reduce_all_steps_with_hint_injects_full_notes_block(
        self, mapped_topic: MappedTopic, notes_hint: TopicsContent
    ) -> None:
        """End-to-end via map_reduce_all_steps: confirms the hint is propagated
        and the full notes block (header + JSON + usage rules) lands in the prompt."""
        fake_response = TopicsContent(topics=[], next_steps=[])

        def fake_map(
            self: Any, chunks: Any
        ) -> tuple[list[list[MappedTopic]], list[int]]:  # noqa: ANN401
            return ([[mapped_topic]], [])

        with (
            patch.object(
                _mrt_module.MapReduceTopics, "_map_chunks_in_parallel", fake_map
            ),
            patch.object(
                _mrt_module,
                "call_llm_with_structured_output",
                return_value=fake_response,
            ) as mock_call,
        ):
            MapReduceTopics().map_reduce_all_steps([], notes_hint=notes_hint)

        prompt = _captured_user_message(mock_call)
        assert "## Notes du rédacteur" in prompt
        assert "### Comment utiliser ces notes" in prompt
        assert notes_hint.model_dump_json() in prompt
