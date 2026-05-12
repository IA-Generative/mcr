import asyncio

from mcr_generation.app.schemas.base import CustomMarkdownReport
from mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline import (
    GenericMapReducePipeline,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class CustomReportGenerator:
    """Async orchestrator (v0) that runs only `GenericMapReducePipeline`.

    Note: does NOT inherit from `BaseReportGenerator` because (a) it's async
    under the hood, and (b) it returns a `CustomMarkdownReport` instead of a
    structured `BaseReport`. The factory exposes a sync `generate()` facade
    via `asyncio.run` for the Celery entrypoint.

    The instruction comes from the constructor argument.
    """

    def __init__(self, instruction: str) -> None:
        self.pipeline = GenericMapReducePipeline()
        self.instruction = instruction

    async def generate_async(self, chunks: list[Chunk]) -> CustomMarkdownReport:
        markdown = await self.pipeline.map_reduce_all_steps(chunks, self.instruction)
        return CustomMarkdownReport(markdown_content=markdown)

    def generate(self, chunks: list[Chunk]) -> CustomMarkdownReport:
        return asyncio.run(self.generate_async(chunks))
