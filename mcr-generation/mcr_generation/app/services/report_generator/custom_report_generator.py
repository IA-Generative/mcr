import asyncio

from mcr_generation.app.schemas.base import CustomMarkdownReport
from mcr_generation.app.schemas.custom_prompt import (
    CollectorSection,
    CustomSection,
    SectionSpec,
)
from mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline import (
    GenericMapReducePipeline,
)
from mcr_generation.app.services.metadata_collectors import METADATA_COLLECTORS
from mcr_generation.app.services.rewriter.rewriter import Rewriter
from mcr_generation.app.services.utils.input_chunker import Chunk


class CustomReportGenerator:
    """Async orchestrator for the custom report flow.

    1. Passes the raw user prompt through the Rewriter to obtain a structured plan.
    2. For each SectionSpec, dispatches either to a predefined metadata collector
       (collector_id set) or to the generic map-reduce pipeline (instruction set).
    3. Concatenates the section bodies into a single markdown blob, keeping the
       current contract with mcr-core (markdown_to_docx).
    """

    def __init__(self, raw_prompt: str) -> None:
        self.raw_prompt = raw_prompt
        self.rewriter = Rewriter()
        self.pipeline = GenericMapReducePipeline()

    async def generate_async(self, chunks: list[Chunk]) -> CustomMarkdownReport:
        plan = await self.rewriter.rewrite(self.raw_prompt)

        bodies = await asyncio.gather(
            *[self._render_section(spec, chunks) for spec in plan.sections]
        )

        markdown = self._assemble_markdown(plan.title, list(plan.sections), bodies)
        return CustomMarkdownReport(markdown_content=markdown)

    def generate(self, chunks: list[Chunk]) -> CustomMarkdownReport:
        return asyncio.run(self.generate_async(chunks))

    async def _render_section(self, spec: SectionSpec, chunks: list[Chunk]) -> str:
        match spec:
            case CollectorSection():
                return await METADATA_COLLECTORS[spec.collector_id].collect(chunks)
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
