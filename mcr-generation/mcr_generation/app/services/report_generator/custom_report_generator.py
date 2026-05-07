import asyncio
import os

from mcr_generation.app.schemas.custom_markdown_report import CustomMarkdownReport
from mcr_generation.app.services.generic_pipeline.generic_map_reduce_pipeline import (
    GenericMapReducePipeline,
)
from mcr_generation.app.services.utils.input_chunker import Chunk

# TODO: Hardcoded for T1b. Will be replaced by the rewriter output in T5.
DEFAULT_INSTRUCTION: str = (
    "Produis un compte rendu de réunion en markdown comportant ces sections :\n"
    "## Risques — liste des risques évoqués\n"
    "## Actions — liste des actions à entreprendre, avec porteur si mentionné\n"
    "## Films & séries — liste les films/séries cités dans la réunion\n"
    "## Blagues — invente une blague liée aux sujets abordés"
)


def _resolve_instruction() -> str:
    return os.environ.get("CUSTOM_USER_PROMPT_FOR_TESTING", DEFAULT_INSTRUCTION)


class CustomReportGenerator:
    """Async orchestrator (v0) that runs only `GenericMapReducePipeline`.

    Note: does NOT inherit from `BaseReportGenerator` because (a) it's async
    under the hood, and (b) it returns a `CustomMarkdownReport` instead of a
    structured `BaseReport`. The factory exposes a sync `generate()` facade
    via `asyncio.run` for the Celery entrypoint.
    """

    def __init__(self) -> None:
        self.pipeline = GenericMapReducePipeline()

    async def generate_async(self, chunks: list[Chunk]) -> CustomMarkdownReport:
        instruction = _resolve_instruction()
        markdown = await self.pipeline.map_reduce_all_steps(chunks, instruction)
        return CustomMarkdownReport(markdown=markdown)

    def generate(self, chunks: list[Chunk]) -> CustomMarkdownReport:
        return asyncio.run(self.generate_async(chunks))
