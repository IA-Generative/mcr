"""Unit tests for services.notes.notes_extractor."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from mcr_generation.app.schemas.base import (
    Intent,
    NextMeeting,
    ParticipantHint,
    ParticipantsHint,
)
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import (
    ExtractedNotes,
    NotesExtractor,
    _NotesFacts,
)
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


def _participants_hint_fixture() -> ParticipantsHint:
    return ParticipantsHint(
        participants=[ParticipantHint(name="Marie", role="Directrice financière")]
    )


_FIXTURES_BY_MODEL: dict[type, Any] = {
    Intent: _intent_fixture,
    NextMeeting: _next_meeting_fixture,
    TopicsContent: _topics_fixture,
    DiscussionsContent: _discussions_fixture,
    ParticipantsHint: _participants_hint_fixture,
}


_DECISION_RECORD_FACETS = frozenset(
    {
        NotesFacet.INTENT,
        NotesFacet.NEXT_MEETING,
        NotesFacet.TOPICS,
        NotesFacet.PARTICIPANTS,
    }
)
_DETAILED_SYNTHESIS_FACETS = frozenset(
    {
        NotesFacet.INTENT,
        NotesFacet.NEXT_MEETING,
        NotesFacet.DISCUSSIONS,
        NotesFacet.PARTICIPANTS,
    }
)


class TestExtractAll:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("facets", "expected_models"),
        [
            pytest.param(
                _DECISION_RECORD_FACETS,
                {Intent, NextMeeting, TopicsContent, ParticipantsHint},
                id="decision_record_facets",
            ),
            pytest.param(
                _DETAILED_SYNTHESIS_FACETS,
                {Intent, NextMeeting, DiscussionsContent, ParticipantsHint},
                id="detailed_synthesis_facets",
            ),
            pytest.param(
                frozenset({NotesFacet.INTENT}),
                {Intent},
                id="single_facet",
            ),
        ],
    )
    async def test_runs_only_requested_facets_and_populates_result(
        self,
        facets: frozenset[NotesFacet],
        expected_models: set[type],
    ) -> None:
        """For each requested facet, the corresponding extract_* method is
        called once with notes_content and its result populates ExtractedNotes;
        non-requested facets stay None."""

        async def _llm_mock(**kwargs: Any) -> Any:
            return _FIXTURES_BY_MODEL[kwargs["response_model"]]()

        with patch(
            f"{_MODULE}.async_call_llm_with_structured_output",
            new=AsyncMock(side_effect=_llm_mock),
        ) as mock_call:
            result = await NotesExtractor().extract_all("notes here", facets=facets)

        assert mock_call.await_count == len(facets)
        models_called = {c.kwargs["response_model"] for c in mock_call.call_args_list}
        assert models_called == expected_models
        for call in mock_call.call_args_list:
            assert "notes here" in call.kwargs["user_message_content"]

        assert (result.intent == _intent_fixture()) == (NotesFacet.INTENT in facets)
        assert (result.next_meeting == _next_meeting_fixture()) == (
            NotesFacet.NEXT_MEETING in facets
        )
        assert (result.topics == _topics_fixture()) == (NotesFacet.TOPICS in facets)
        assert (result.discussions == _discussions_fixture()) == (
            NotesFacet.DISCUSSIONS in facets
        )
        assert (result.participants == _participants_hint_fixture()) == (
            NotesFacet.PARTICIPANTS in facets
        )
        assert result.custom_section_facts is None

    @pytest.mark.asyncio
    async def test_short_circuits_when_no_facets_and_no_instructions(self) -> None:
        """Empty facets AND empty custom_instructions short-circuits: no
        extract_* call, no truncation, returns ExtractedNotes() with all
        fields None."""
        extractor = NotesExtractor()
        with (
            patch.object(
                extractor, "extract_intent", new_callable=AsyncMock
            ) as m_intent,
            patch.object(
                extractor, "extract_next_meeting", new_callable=AsyncMock
            ) as m_nm,
            patch.object(
                extractor, "extract_topics_hint", new_callable=AsyncMock
            ) as m_topics,
            patch.object(
                extractor, "extract_discussions_hint", new_callable=AsyncMock
            ) as m_discussions,
            patch.object(
                extractor, "_extract_custom_facts", new_callable=AsyncMock
            ) as m_custom,
            patch.object(extractor, "_truncate_if_too_long") as m_trunc,
        ):
            result = await extractor.extract_all(
                "any content", facets=frozenset(), custom_instructions=[]
            )

        assert result == ExtractedNotes()
        m_intent.assert_not_called()
        m_nm.assert_not_called()
        m_topics.assert_not_called()
        m_discussions.assert_not_called()
        m_custom.assert_not_called()
        m_trunc.assert_not_called()

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
            patch.object(
                NotesExtractor,
                "extract_participants_hint",
                new_callable=AsyncMock,
                return_value=_participants_hint_fixture(),
            ),
            patch(
                f"{_MODULE}.record_notes_extraction_failed_event"
            ) as mock_record_failure,
        ):
            result = await NotesExtractor().extract_all(
                "notes", facets=_DECISION_RECORD_FACETS
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
            patch.object(
                NotesExtractor,
                "extract_participants_hint",
                new_callable=AsyncMock,
                return_value=_participants_hint_fixture(),
            ),
            patch(f"{_MODULE}.record_notes_truncated_event") as mock_record_trunc,
            patch(f"{_MODULE}.logger") as mock_logger,
        ):
            extractor = NotesExtractor()
            max_len = extractor.chunking_config.CHUNK_SIZE
            await extractor.extract_all(long_notes, facets=_DECISION_RECORD_FACETS)

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
            patch.object(
                NotesExtractor,
                "extract_participants_hint",
                new_callable=AsyncMock,
                return_value=_participants_hint_fixture(),
            ),
            patch(f"{_MODULE}.record_notes_truncated_event") as mock_record_trunc,
        ):
            short_notes = "hello"
            await NotesExtractor().extract_all(
                short_notes, facets=_DECISION_RECORD_FACETS
            )

            mock_intent.assert_awaited_once_with(short_notes)
            mock_record_trunc.assert_not_called()


class TestExtractCustomFacts:
    @pytest.mark.asyncio
    async def test_returns_llm_facts_and_passes_instruction_and_notes_in_prompt(
        self,
    ) -> None:
        expected = ["fact 1", "fact 2"]
        with patch(
            f"{_MODULE}.async_call_llm_with_structured_output",
            new=AsyncMock(return_value=_NotesFacts(facts=expected)),
        ) as mock_call:
            result = await NotesExtractor()._extract_custom_facts(
                "raw notes here", "liste les engagements"
            )

        assert result == expected
        prompt = mock_call.call_args.kwargs["user_message_content"]
        assert "raw notes here" in prompt
        assert "liste les engagements" in prompt

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_llm_error(self) -> None:
        with (
            patch(
                f"{_MODULE}.async_call_llm_with_structured_output",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch(
                f"{_MODULE}.record_notes_extraction_failed_event"
            ) as mock_record_failure,
        ):
            result = await NotesExtractor()._extract_custom_facts("notes", "consigne")

        assert result == []
        mock_record_failure.assert_called_once()
        assert mock_record_failure.call_args.kwargs["theme"] == "custom_facts"
        assert mock_record_failure.call_args.kwargs["exception_type"] == "RuntimeError"


class TestExtractAllWithCustomInstructions:
    @pytest.mark.asyncio
    async def test_only_custom_instructions_populates_dict_and_leaves_facets_none(
        self,
    ) -> None:
        async def _fake(self: NotesExtractor, notes: str, instr: str) -> list[str]:
            return [f"fact for {instr}"]

        with patch.object(NotesExtractor, "_extract_custom_facts", new=_fake):
            result = await NotesExtractor().extract_all(
                "notes", custom_instructions=["A", "B"]
            )

        assert result.intent is None
        assert result.next_meeting is None
        assert result.topics is None
        assert result.discussions is None
        assert result.custom_section_facts == {
            "A": ["fact for A"],
            "B": ["fact for B"],
        }

    @pytest.mark.asyncio
    async def test_combined_facets_and_custom_runs_in_single_gather(self) -> None:
        async def _fake_custom(
            self: NotesExtractor, notes: str, instr: str
        ) -> list[str]:
            return [f"f-{instr}"]

        with (
            patch.object(
                NotesExtractor,
                "extract_intent",
                new_callable=AsyncMock,
                return_value=_intent_fixture(),
            ) as m_intent,
            patch.object(NotesExtractor, "_extract_custom_facts", new=_fake_custom),
        ):
            result = await NotesExtractor().extract_all(
                "notes",
                facets=frozenset({NotesFacet.INTENT}),
                custom_instructions=["X"],
            )

        m_intent.assert_awaited_once_with("notes")
        assert result.intent == _intent_fixture()
        assert result.custom_section_facts == {"X": ["f-X"]}
