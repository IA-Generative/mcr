import asyncio

from mcr_generation.app.schemas.base import CustomMarkdownReport
from mcr_generation.app.schemas.custom_prompt import (
    CollectorSection,
    CustomSection,
    RewriterOutput,
    SectionSpec,
)
from mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline import (
    GenericMapReducePipeline,
)
from mcr_generation.app.services.metadata_collectors import METADATA_COLLECTORS
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import (
    ExtractedNotes,
    NotesExtractor,
)
from mcr_generation.app.services.rewriter.rewriter import Rewriter
from mcr_generation.app.services.utils.input_chunker import Chunk


class CustomReportGenerator:
    """Async orchestrator for the custom report flow.

    1. Pass the raw user prompt through the Rewriter to obtain a structured plan.
    2. If notes_content is provided, extract the union of notes facets advertised
       by the CollectorSections present in the plan.
    3. For each SectionSpec, dispatch either to a predefined metadata collector
       (collector_id set) or to the generic map-reduce pipeline (instruction set).
    4. Concatenate the section bodies into a single markdown blob, keeping the
       current contract with mcr-core (markdown_to_docx).
    """

    def __init__(self, raw_prompt: str) -> None:
        self.raw_prompt = raw_prompt
        self.rewriter = Rewriter()
        self.pipeline = GenericMapReducePipeline()

    async def generate_async(
        self,
        chunks: list[Chunk],
        notes_content: str | None = None,
    ) -> CustomMarkdownReport:
        plan = await self.rewriter.rewrite(self.raw_prompt)
        extracted_notes = await self._extract_notes_for_plan(plan, notes_content)

        bodies = await asyncio.gather(
            *[
                self._render_section(spec, chunks, extracted_notes)
                for spec in plan.sections
            ]
        )

        markdown = self._assemble_markdown(plan.title, list(plan.sections), bodies)
        return CustomMarkdownReport(markdown_content=markdown)

    def generate(
        self,
        chunks: list[Chunk],
        notes_content: str | None = None,
    ) -> CustomMarkdownReport:
        return asyncio.run(self.generate_async(chunks, notes_content))

    async def _extract_notes_for_plan(
        self,
        plan: RewriterOutput,
        notes_content: str | None,
    ) -> ExtractedNotes | None:
        """Compute the union of notes facets advertised by the CollectorSections
        of the plan and run `NotesExtractor` against it.

        Short-circuits to `None` (no LLM call) when notes_content is empty/blank
        or when no CollectorSection in the plan needs any facet.
        """
        if notes_content is None or not notes_content.strip():
            return None

        facets: frozenset[NotesFacet] = frozenset().union(
            *(
                METADATA_COLLECTORS[spec.collector_id].notes_facets
                for spec in plan.sections
                if isinstance(spec, CollectorSection)
            )
        )
        if not facets:
            return None

        return await NotesExtractor().extract_all(notes_content, facets=facets)

    async def _render_section(
        self,
        spec: SectionSpec,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None,
    ) -> str:
        match spec:
            case CollectorSection():
                return await METADATA_COLLECTORS[spec.collector_id].collect(
                    chunks, extracted_notes=extracted_notes
                )
            case CustomSection():
                return await self.pipeline.map_reduce_all_steps(
                    chunks, spec.instruction
                )

    def _assemble_markdown(
        self,
        title: str | None,
        sections: list[SectionSpec],
        bodies: list[str],
    ) -> str:
        parts: list[str] = []
        if title is not None:
            parts.append(f"# {title}")
        for spec, body in zip(sections, bodies, strict=True):
            parts.append(f"## {spec.heading}\n\n{body}")
        return "\n\n".join(parts)
