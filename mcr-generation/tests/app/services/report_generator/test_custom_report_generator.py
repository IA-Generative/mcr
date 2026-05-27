from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcr_generation.app.exceptions.exceptions import MissingCustomPromptError
from mcr_generation.app.schemas.base import CustomMarkdownReport
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.schemas.custom_prompt import (
    CollectorSection,
    CustomSection,
    RewriterOutput,
)
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.report_generator import create_report_generator
from mcr_generation.app.services.report_generator.custom_report_generator import (
    CustomReportGenerator,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

_MODULE = "mcr_generation.app.services.report_generator.custom_report_generator"


def _stub_collector(notes_facets: frozenset[NotesFacet] = frozenset()) -> MagicMock:
    collector = MagicMock()
    collector.notes_facets = notes_facets
    collector.collect = AsyncMock(return_value="- body")
    return collector


@pytest.mark.asyncio
@patch(f"{_MODULE}.METADATA_COLLECTORS")
async def test_generate_async_dispatches_collector_and_generic(
    mock_registry: MagicMock,
) -> None:
    mock_collector = MagicMock()
    mock_collector.notes_facets = frozenset()
    mock_collector.collect = AsyncMock(return_value="- Alice\n- Bob")
    mock_registry.__getitem__.return_value = mock_collector

    plan = RewriterOutput(
        title="Réunion sprint",
        sections=[
            CollectorSection(heading="Participants", collector_id="participants"),
            CustomSection(heading="Risques", instruction="Liste les risques évoqués"),
        ],
    )

    gen = CustomReportGenerator(raw_prompt="prompt brut")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(return_value="- R1\n- R2")

    chunks = [Chunk(text="contenu réunion", id=0)]
    report = await gen.generate_async(chunks)

    assert isinstance(report, CustomMarkdownReport)
    assert report.markdown_content == (
        "# Réunion sprint\n\n"
        "## Participants\n\n- Alice\n- Bob\n\n"
        "## Risques\n\n- R1\n- R2"
    )

    gen.rewriter.rewrite.assert_awaited_once_with("prompt brut")
    mock_collector.collect.assert_awaited_once_with(chunks, extracted_notes=None)
    gen.pipeline.map_reduce_all_steps.assert_awaited_once_with(
        chunks, "Liste les risques évoqués", notes_facts=None
    )


@pytest.mark.asyncio
async def test_generate_async_omits_h1_when_title_is_none() -> None:
    plan = RewriterOutput(
        title=None,
        sections=[CustomSection(heading="Risques", instruction="Liste les risques")],
    )
    gen = CustomReportGenerator(raw_prompt="prompt")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(return_value="- R1")

    report = await gen.generate_async([Chunk(text="x", id=0)])

    assert report.markdown_content == "## Risques\n\n- R1"


def test_factory_raises_when_custom_prompt_missing() -> None:
    with pytest.raises(MissingCustomPromptError):
        create_report_generator(ReportTypes.CUSTOM_REPORT)


# ---------------------------------------------------------------------------
# Notes extraction wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(f"{_MODULE}.NotesExtractor")
async def test_notes_extracted_with_facets_union_and_dispatched_to_collectors(
    mock_notes_extractor_cls: MagicMock,
) -> None:
    extracted = ExtractedNotes()
    mock_notes_extractor_cls.return_value.extract_all = AsyncMock(
        return_value=extracted
    )

    plan = RewriterOutput(
        title=None,
        sections=[
            CollectorSection(heading="Titre", collector_id="title"),
            CollectorSection(heading="Sujets", collector_id="topics"),
        ],
    )
    gen = CustomReportGenerator(raw_prompt="prompt")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)

    title_collector = _stub_collector(frozenset({NotesFacet.INTENT}))
    topics_collector = _stub_collector(
        frozenset({NotesFacet.INTENT, NotesFacet.TOPICS})
    )

    def lookup(collector_id: str) -> MagicMock:
        return {"title": title_collector, "topics": topics_collector}[collector_id]

    with patch(f"{_MODULE}.METADATA_COLLECTORS") as mock_registry:
        mock_registry.__getitem__.side_effect = lookup
        await gen.generate_async([Chunk(text="x", id=0)], notes_content="some notes")

    mock_notes_extractor_cls.return_value.extract_all.assert_awaited_once_with(
        "some notes",
        facets=frozenset({NotesFacet.INTENT, NotesFacet.TOPICS}),
        custom_instructions=[],
    )
    title_collector.collect.assert_awaited_once_with(
        [Chunk(text="x", id=0)], extracted_notes=extracted
    )
    topics_collector.collect.assert_awaited_once_with(
        [Chunk(text="x", id=0)], extracted_notes=extracted
    )


@pytest.mark.asyncio
@patch(f"{_MODULE}.NotesExtractor")
async def test_no_notes_extraction_when_no_facets_and_no_custom_sections(
    mock_notes_extractor_cls: MagicMock,
) -> None:
    """Plan with only a CollectorSection without notes_facets and no
    CustomSection → both facets and custom_instructions are empty; the
    short-circuit prevents any LLM call even when notes_content is provided."""
    plan = RewriterOutput(
        title=None,
        sections=[
            CollectorSection(heading="Participants", collector_id="participants"),
        ],
    )
    gen = CustomReportGenerator(raw_prompt="prompt")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)

    with patch(f"{_MODULE}.METADATA_COLLECTORS") as mock_registry:
        mock_registry.__getitem__.return_value = _stub_collector(frozenset())
        await gen.generate_async([Chunk(text="x", id=0)], notes_content="some notes")

    mock_notes_extractor_cls.assert_not_called()


@pytest.mark.asyncio
@patch(f"{_MODULE}.NotesExtractor")
async def test_notes_extracted_with_collector_facets_and_custom_instructions(
    mock_notes_extractor_cls: MagicMock,
) -> None:
    """Plan with a notes-aware CollectorSection AND a CustomSection → facets
    contains the collector's notes_facets and custom_instructions contains the
    CustomSection's instruction; both are passed to NotesExtractor."""
    extracted = ExtractedNotes(custom_section_facts={"Liste les risques": ["r1"]})
    mock_notes_extractor_cls.return_value.extract_all = AsyncMock(
        return_value=extracted
    )

    plan = RewriterOutput(
        title=None,
        sections=[
            CollectorSection(heading="Sujets", collector_id="topics"),
            CustomSection(heading="Risques", instruction="Liste les risques"),
        ],
    )
    gen = CustomReportGenerator(raw_prompt="prompt")
    gen.rewriter = MagicMock()
    gen.rewriter.rewrite = AsyncMock(return_value=plan)
    gen.pipeline = MagicMock()
    gen.pipeline.map_reduce_all_steps = AsyncMock(return_value="- R")

    topics_collector = _stub_collector(
        frozenset({NotesFacet.INTENT, NotesFacet.TOPICS})
    )

    with patch(f"{_MODULE}.METADATA_COLLECTORS") as mock_registry:
        mock_registry.__getitem__.return_value = topics_collector
        await gen.generate_async([Chunk(text="x", id=0)], notes_content="some notes")

    mock_notes_extractor_cls.return_value.extract_all.assert_awaited_once_with(
        "some notes",
        facets=frozenset({NotesFacet.INTENT, NotesFacet.TOPICS}),
        custom_instructions=["Liste les risques"],
    )
    topics_collector.collect.assert_awaited_once_with(
        [Chunk(text="x", id=0)], extracted_notes=extracted
    )
    gen.pipeline.map_reduce_all_steps.assert_awaited_once_with(
        [Chunk(text="x", id=0)], "Liste les risques", notes_facts=["r1"]
    )
