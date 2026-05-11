"""Unit tests for services.notes.notes_extractor."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from mcr_generation.app.schemas.base import Intent, NextMeeting
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.notes.notes_extractor import NotesExtractor
from mcr_generation.app.services.sections.detailed_discussions.types import (
    DiscussionsContent,
)
from mcr_generation.app.services.sections.topics.types import TopicsContent

_MODULE = "mcr_generation.app.services.notes.notes_extractor"


def _intent_fixture() -> Intent:
    return Intent(
        title="Réunion budget",
        objective="Valider le budget",
        confidence=0.8,
        justification="Mentionné explicitement",
    )


def _next_meeting_fixture() -> NextMeeting:
    return NextMeeting(
        date="15/03/2026",
        time="10:00",
        purpose="Suivi budget",
        confidence=0.7,
        justification="Date annoncée",
    )


def _topics_fixture() -> TopicsContent:
    return TopicsContent(topics=[], next_steps=[])


def _discussions_fixture() -> DiscussionsContent:
    return DiscussionsContent(detailed_discussions=[])


def _fake_llm_side_effect(**kwargs: Any) -> BaseModel:
    """Routes an async LLM call to the right Pydantic fixture based on its
    response_model. Used by integration tests to mock the LLM helper while
    still letting NotesExtractor exercise its full code path."""
    response_model = kwargs["response_model"]
    if response_model is Intent:
        return _intent_fixture()
    if response_model is NextMeeting:
        return _next_meeting_fixture()
    if response_model is TopicsContent:
        return _topics_fixture()
    if response_model is DiscussionsContent:
        return _discussions_fixture()
    raise AssertionError(f"unexpected response_model: {response_model}")


class TestExtractAll:
    @pytest.mark.asyncio
    async def test_decision_record_integration(self) -> None:
        """Integration: extract_all in DECISION_RECORD mode triggers 3 LLM
        calls (Intent + NextMeeting + TopicsContent) with the notes content
        in the prompt and produces the expected ExtractedNotes."""
        with patch(
            f"{_MODULE}.async_call_llm_with_structured_output",
            new_callable=AsyncMock,
            side_effect=_fake_llm_side_effect,
        ) as mock_call:
            result = await NotesExtractor().extract_all(
                "notes here", report_type=ReportTypes.DECISION_RECORD
            )

            assert result.intent == _intent_fixture()
            assert result.next_meeting == _next_meeting_fixture()
            assert result.topics == _topics_fixture()
            assert result.discussions is None

            assert mock_call.await_count == 3
            models_called = {
                c.kwargs["response_model"] for c in mock_call.call_args_list
            }
            assert models_called == {Intent, NextMeeting, TopicsContent}
            for call in mock_call.call_args_list:
                assert "notes here" in call.kwargs["user_message_content"]

    @pytest.mark.asyncio
    async def test_detailed_synthesis_integration(self) -> None:
        """Integration: extract_all in DETAILED_SYNTHESIS mode triggers 3 LLM
        calls (Intent + NextMeeting + DiscussionsContent) and leaves topics
        unset."""
        with patch(
            f"{_MODULE}.async_call_llm_with_structured_output",
            new_callable=AsyncMock,
            side_effect=_fake_llm_side_effect,
        ) as mock_call:
            result = await NotesExtractor().extract_all(
                "notes here", report_type=ReportTypes.DETAILED_SYNTHESIS
            )

            assert result.intent == _intent_fixture()
            assert result.next_meeting == _next_meeting_fixture()
            assert result.discussions == _discussions_fixture()
            assert result.topics is None

            assert mock_call.await_count == 3
            models_called = {
                c.kwargs["response_model"] for c in mock_call.call_args_list
            }
            assert models_called == {Intent, NextMeeting, DiscussionsContent}

    @pytest.mark.asyncio
    async def test_returns_partial_result_on_partial_failure(self) -> None:
        with (
            patch.object(
                NotesExtractor,
                "extract_intent",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch.object(
                NotesExtractor,
                "extract_next_meeting",
                new_callable=AsyncMock,
                return_value=_next_meeting_fixture(),
            ),
            patch.object(
                NotesExtractor,
                "extract_topics_hint",
                new_callable=AsyncMock,
                return_value=_topics_fixture(),
            ),
            patch(
                f"{_MODULE}.record_notes_extraction_failed_event"
            ) as mock_record_failure,
        ):
            result = await NotesExtractor().extract_all(
                "notes", report_type=ReportTypes.DECISION_RECORD
            )

            assert result.intent is None
            assert result.next_meeting == _next_meeting_fixture()
            assert result.topics == _topics_fixture()
            mock_record_failure.assert_called_once()
            assert mock_record_failure.call_args.kwargs["theme"] == "intent"
            assert mock_record_failure.call_args.kwargs["exception_type"] == (
                "RuntimeError"
            )

    @pytest.mark.asyncio
    async def test_truncates_long_notes_and_warns(self) -> None:
        long_notes = "x" * 25000  # CHUNK_SIZE default is 20000

        with (
            patch.object(
                NotesExtractor,
                "extract_intent",
                new_callable=AsyncMock,
                return_value=_intent_fixture(),
            ) as mock_intent,
            patch.object(
                NotesExtractor,
                "extract_next_meeting",
                new_callable=AsyncMock,
                return_value=_next_meeting_fixture(),
            ),
            patch.object(
                NotesExtractor,
                "extract_topics_hint",
                new_callable=AsyncMock,
                return_value=_topics_fixture(),
            ),
            patch(f"{_MODULE}.record_notes_truncated_event") as mock_record_trunc,
            patch(f"{_MODULE}.logger") as mock_logger,
        ):
            extractor = NotesExtractor()
            max_len = extractor.chunking_config.CHUNK_SIZE
            await extractor.extract_all(
                long_notes, report_type=ReportTypes.DECISION_RECORD
            )

            passed_notes = mock_intent.call_args.args[0]
            assert len(passed_notes) == max_len
            mock_logger.warning.assert_called_once()
            mock_record_trunc.assert_called_once_with(
                original_length=25000, truncated_length=max_len
            )

    @pytest.mark.asyncio
    async def test_does_not_truncate_short_notes(self) -> None:
        with (
            patch.object(
                NotesExtractor,
                "extract_intent",
                new_callable=AsyncMock,
                return_value=_intent_fixture(),
            ) as mock_intent,
            patch.object(
                NotesExtractor,
                "extract_next_meeting",
                new_callable=AsyncMock,
                return_value=_next_meeting_fixture(),
            ),
            patch.object(
                NotesExtractor,
                "extract_topics_hint",
                new_callable=AsyncMock,
                return_value=_topics_fixture(),
            ),
            patch(f"{_MODULE}.record_notes_truncated_event") as mock_record_trunc,
        ):
            short_notes = "hello"
            await NotesExtractor().extract_all(
                short_notes, report_type=ReportTypes.DECISION_RECORD
            )

            mock_intent.assert_awaited_once_with(short_notes)
            mock_record_trunc.assert_not_called()
