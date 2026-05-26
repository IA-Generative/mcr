"""Unit tests for metadata collectors (T2).

Each collector wraps a sync extractor — we mock the extractor class to a
MagicMock returning a Pydantic-shaped result, then assert the collector's
markdown rendering. `_to_markdown` is also exercised directly (no thread)
to keep the assertion easy to read.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcr_generation.app.schemas.base import (
    DetailedDiscussion,
    Intent,
    NextMeeting,
    Participant,
    Participants,
    ParticipantsWithThinkingListWrapper,
    ParticipantWithThinking,
    Topic,
)
from mcr_generation.app.services.metadata_collectors import METADATA_COLLECTORS
from mcr_generation.app.services.metadata_collectors.base import (
    MetadataCollector,
    register,
)
from mcr_generation.app.services.metadata_collectors.detailed_discussions_collector import (  # noqa: E501
    DetailedDiscussionsCollector,
)
from mcr_generation.app.services.metadata_collectors.next_meeting_collector import (
    NextMeetingCollector,
)
from mcr_generation.app.services.metadata_collectors.participants_collector import (
    ParticipantsCollector,
)
from mcr_generation.app.services.metadata_collectors.title_collector import (
    TitleCollector,
)
from mcr_generation.app.services.metadata_collectors.topics_collector import (
    TopicsCollector,
)
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.sections.detailed_discussions.types import (
    DiscussionsContent,
)
from mcr_generation.app.services.sections.topics.types import TopicsContent
from mcr_generation.app.services.utils.input_chunker import Chunk

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_contains_expected_ids() -> None:
    assert set(METADATA_COLLECTORS.keys()) == {
        "title",
        "participants",
        "next_meeting",
        "topics",
        "detailed_discussions",
    }


def test_registry_entries_have_description() -> None:
    for collector in METADATA_COLLECTORS.values():
        assert isinstance(collector.description, str) and collector.description


def test_register_rejects_id_not_in_literal() -> None:
    class BogusCollector(MetadataCollector):
        id = "nope"  # type: ignore[assignment]
        description = "bogus"

        def _extract(
            self,
            chunks: list[Chunk],
            extracted_notes: ExtractedNotes | None = None,
        ) -> Any:
            return None

        def _to_markdown(self, result: Any) -> str:
            return ""

    with pytest.raises(RuntimeError, match="not in CollectorId Literal"):
        register(BogusCollector())


# ---------------------------------------------------------------------------
# Collect orchestration (base class behavior)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_runs_extract_in_thread_and_formats() -> None:
    """The base `collect` must push `_extract` into a thread and pipe the result
    through `_to_markdown`."""
    collector = ParticipantsCollector()
    sentinel = MagicMock()
    collector._extract = MagicMock(return_value=sentinel)  # type: ignore[method-assign]
    collector._to_markdown = MagicMock(return_value="## md")  # type: ignore[method-assign]

    with patch(
        "mcr_generation.app.services.metadata_collectors.base.asyncio.to_thread",
        new=AsyncMock(return_value=sentinel),
    ) as mock_to_thread:
        md = await collector.collect([Chunk(text="x", id=0)])

    assert md == "## md"
    mock_to_thread.assert_awaited_once_with(
        collector._extract, [Chunk(text="x", id=0)], None
    )
    collector._to_markdown.assert_called_once_with(sentinel)


# ---------------------------------------------------------------------------
# TitleCollector
# ---------------------------------------------------------------------------


def _intent(
    title: str | None = "Réunion Budget",
    objective: str | None = "Valider le budget",
) -> Intent:
    return Intent(
        title=title,
        objective=objective,
        confidence=0.9,
        justification="ok",
    )


def test_title_to_markdown_renders_title_and_objective() -> None:
    md = TitleCollector()._to_markdown(_intent())
    assert md.startswith("**Réunion Budget**")
    assert "_Objectif : Valider le budget_" in md


def test_title_to_markdown_handles_missing_title() -> None:
    md = TitleCollector()._to_markdown(_intent(title=None, objective=None))
    assert "_Titre non identifié_" in md


@patch("mcr_generation.app.services.metadata_collectors.title_collector.RefineIntent")
def test_title_collector_propagates_intent_hint(mock_cls: MagicMock) -> None:
    intent = _intent(title="From notes")
    mock_cls.return_value.init_then_refine.return_value = intent

    TitleCollector()._extract(
        [Chunk(text="x", id=0)], extracted_notes=ExtractedNotes(intent=intent)
    )

    mock_cls.return_value.init_then_refine.assert_called_once_with(
        [Chunk(text="x", id=0)], init_hint=intent
    )


# ---------------------------------------------------------------------------
# ParticipantsCollector
# ---------------------------------------------------------------------------


def _participant(
    speaker_id: str = "LOCUTEUR_00",
    name: str | None = "Alice",
    role: str | None = "PO",
) -> Participant:
    return Participant(
        speaker_id=speaker_id,
        name=name,
        role=role,
        confidence=0.9,
        association_justification="ok",
    )


def test_participants_to_markdown_lists_each_participant() -> None:
    md = ParticipantsCollector()._to_markdown(
        Participants(participants=[_participant(name="Alice", role="PO")])
    )
    assert "**Alice**" in md
    assert "PO" in md
    assert not md.lstrip().startswith("#")


def test_participants_to_markdown_falls_back_to_speaker_id() -> None:
    md = ParticipantsCollector()._to_markdown(
        Participants(participants=[_participant(name=None, role=None)])
    )
    assert "**LOCUTEUR_00**" in md


def test_participants_to_markdown_handles_empty_list() -> None:
    md = ParticipantsCollector()._to_markdown(Participants(participants=[]))
    assert md == "_Aucun participant identifié._"


# ---------------------------------------------------------------------------
# NextMeetingCollector
# ---------------------------------------------------------------------------


@patch(
    "mcr_generation.app.services.metadata_collectors.next_meeting_collector.format_next_meeting_for_report",
    return_value="Suivi budget\nDate et heure prévues: 15/03/2026 - 10:00",
)
def test_next_meeting_to_markdown_renders_when_reliable(_mock: MagicMock) -> None:
    md = NextMeetingCollector()._to_markdown(
        NextMeeting(
            date="15/03/2026",
            time="10:00",
            purpose="Suivi budget",
            confidence=0.9,
            justification="ok",
        )
    )
    assert "Suivi budget" in md
    assert "15/03/2026" in md
    assert not md.lstrip().startswith("#")


@patch(
    "mcr_generation.app.services.metadata_collectors.next_meeting_collector.format_next_meeting_for_report",
    return_value=None,
)
def test_next_meeting_to_markdown_falls_back_on_low_confidence(
    _mock: MagicMock,
) -> None:
    md = NextMeetingCollector()._to_markdown(
        NextMeeting(
            date=None,
            time=None,
            purpose=None,
            confidence=0.1,
            justification="ok",
        )
    )
    assert md == "_Pas de prochaine réunion mentionnée._"


@patch(
    "mcr_generation.app.services.metadata_collectors.next_meeting_collector.RefineNextMeeting"
)
def test_next_meeting_collector_propagates_next_meeting_hint(
    mock_cls: MagicMock,
) -> None:
    nm = NextMeeting(
        date="15/03/2026",
        time="10:00",
        purpose="Suivi",
        confidence=0.9,
        justification="ok",
    )
    mock_cls.return_value.init_then_refine.return_value = nm

    NextMeetingCollector()._extract(
        [Chunk(text="x", id=0)], extracted_notes=ExtractedNotes(next_meeting=nm)
    )

    mock_cls.return_value.init_then_refine.assert_called_once_with(
        [Chunk(text="x", id=0)], init_hint=nm
    )


# ---------------------------------------------------------------------------
# TopicsCollector
# ---------------------------------------------------------------------------


def _topic(
    title: str = "Budget marketing",
    introduction_text: str | None = "Discussion du budget marketing.",
    details: list[str] | None = None,
    main_decision: str | None = "Réduire de 10%",
) -> Topic:
    return Topic(
        title=title,
        introduction_text=introduction_text,
        details=details if details is not None else ["Budget actuel: 50k€"],
        main_decision=main_decision,
    )


def test_topics_to_markdown_renders_topics_and_next_steps() -> None:
    md = TopicsCollector()._to_markdown(
        TopicsContent(
            topics=[_topic()],
            next_steps=["Envoyer le CR"],
        )
    )
    assert "### Sujets et décisions" in md
    assert "#### Budget marketing" in md
    assert "**Décision** : Réduire de 10%" in md
    assert "### Prochaines étapes" in md
    assert "- Envoyer le CR" in md
    assert not md.lstrip().startswith("## ")


def test_topics_to_markdown_handles_empty_content() -> None:
    md = TopicsCollector()._to_markdown(TopicsContent(topics=[], next_steps=[]))
    assert md == "_Aucun sujet ni étape identifiés._"


@patch(
    "mcr_generation.app.services.metadata_collectors.topics_collector.MapReduceTopics"
)
@patch(
    "mcr_generation.app.services.metadata_collectors.topics_collector.RefineParticipants"
)
@patch("mcr_generation.app.services.metadata_collectors.topics_collector.RefineIntent")
def test_topics_collector_propagates_intent_and_topics_hints(
    mock_intent_cls: MagicMock,
    mock_participants_cls: MagicMock,
    mock_topics_cls: MagicMock,
) -> None:
    intent = _intent(title="From notes")
    topics = TopicsContent(topics=[_topic()], next_steps=[])
    mock_intent_cls.return_value.init_then_refine.return_value = intent
    mock_participants_cls.return_value.init_then_refine.return_value.to_public.return_value = MagicMock(
        participants=[]
    )

    TopicsCollector()._extract(
        [Chunk(text="x", id=0)],
        extracted_notes=ExtractedNotes(intent=intent, topics=topics),
    )

    mock_intent_cls.return_value.init_then_refine.assert_called_once_with(
        [Chunk(text="x", id=0)], init_hint=intent
    )
    mock_topics_cls.return_value.map_reduce_all_steps.assert_called_once_with(
        [Chunk(text="x", id=0)], notes_hint=topics
    )


# ---------------------------------------------------------------------------
# DetailedDiscussionsCollector
# ---------------------------------------------------------------------------


def _discussion(**kwargs: Any) -> DetailedDiscussion:
    defaults: dict[str, Any] = {
        "title": "Préparation démo",
        "key_ideas": ["Préparer un POC"],
        "decisions": ["GO sur la démo"],
        "actions": ["Réserver la salle"],
        "focus_points": ["Risque planning"],
    }
    defaults.update(kwargs)
    return DetailedDiscussion(**defaults)


def test_detailed_discussions_to_markdown_renders_all_sections() -> None:
    md = DetailedDiscussionsCollector()._to_markdown(
        DiscussionsContent(detailed_discussions=[_discussion()])
    )
    assert md.startswith("### Préparation démo")
    assert "**Idées clés**" in md
    assert "- Préparer un POC" in md
    assert "**Décisions**" in md
    assert "**Actions**" in md
    assert "**Points de vigilance**" in md


def test_detailed_discussions_to_markdown_handles_empty_list() -> None:
    md = DetailedDiscussionsCollector()._to_markdown(
        DiscussionsContent(detailed_discussions=[])
    )
    assert md == "_Aucune discussion détaillée identifiée._"


@patch(
    "mcr_generation.app.services.metadata_collectors.detailed_discussions_collector.MapReduceDetailedDiscussions"
)
@patch(
    "mcr_generation.app.services.metadata_collectors.detailed_discussions_collector.RefineParticipants"
)
@patch(
    "mcr_generation.app.services.metadata_collectors.detailed_discussions_collector.RefineIntent"
)
def test_detailed_discussions_collector_propagates_intent_and_discussions_hints(
    mock_intent_cls: MagicMock,
    mock_participants_cls: MagicMock,
    mock_dd_cls: MagicMock,
) -> None:
    intent = _intent(title="From notes")
    discussions = DiscussionsContent(detailed_discussions=[_discussion()])
    mock_intent_cls.return_value.init_then_refine.return_value = intent
    mock_participants_cls.return_value.init_then_refine.return_value.to_public.return_value = MagicMock(
        participants=[]
    )

    DetailedDiscussionsCollector()._extract(
        [Chunk(text="x", id=0)],
        extracted_notes=ExtractedNotes(intent=intent, discussions=discussions),
    )

    mock_intent_cls.return_value.init_then_refine.assert_called_once_with(
        [Chunk(text="x", id=0)], init_hint=intent
    )
    mock_dd_cls.return_value.map_reduce_all_steps.assert_called_once_with(
        [Chunk(text="x", id=0)], notes_hint=discussions
    )


# ---------------------------------------------------------------------------
# End-to-end: collect() via the registry, with the legacy extractor patched.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(
    "mcr_generation.app.services.metadata_collectors.participants_collector.RefineParticipants"
)
async def test_participants_collect_end_to_end(mock_cls: MagicMock) -> None:
    mock_cls.return_value.init_then_refine.return_value = (
        ParticipantsWithThinkingListWrapper(
            participants=[
                ParticipantWithThinking(
                    speaker_id="LOCUTEUR_00",
                    name="Alice",
                    role="PO",
                    confidence=0.9,
                    association_justification="ok",
                )
            ]
        )
    )

    md = await METADATA_COLLECTORS["participants"].collect([Chunk(text="x", id=0)])

    assert "**Alice**" in md
    assert not md.lstrip().startswith("#")
    mock_cls.return_value.init_then_refine.assert_called_once()
