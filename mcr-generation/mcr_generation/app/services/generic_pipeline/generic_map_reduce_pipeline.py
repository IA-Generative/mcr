"""Generic async map-reduce pipeline producing markdown.

The instruction string is injected verbatim into both map and reduce prompts.
Callers (rewriter / orchestrator) are responsible for crafting the instruction.
"""

import asyncio
import re

import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.exceptions.exceptions import EmptyChunksError
from mcr_generation.app.services.generic_pipeline.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.notes.prompts import NOTES_SECTION_TEMPLATE
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.llm_helpers import (
    async_call_llm_with_structured_output,
)
from mcr_generation.app.utils.function_execution_timer import log_execution_time
from mcr_generation.app.utils.langfuse_observability import (
    record_empty_map_phase_event,
)


class _MapResponse(BaseModel):
    facts: list[str] = Field(default_factory=list)


_FORBIDDEN_HEADING_RE = re.compile(r"^#{1,2}\s", re.MULTILINE)


class _ReduceResponse(BaseModel):
    markdown: str

    @field_validator("markdown")
    @classmethod
    def _no_top_level_heading(cls, value: str) -> str:
        if _FORBIDDEN_HEADING_RE.search(value):
            raise ValueError(
                "markdown must not contain top-level headings (`# ` or `## `). "
                "The section title is added by the caller. "
                "Use `###`/`####` for sub-headings instead."
            )
        return value


class GenericMapReducePipeline:
    """Generic async map-reduce engine producing markdown."""

    def __init__(self, max_concurrency: int = 4) -> None:
        self.llm_config = LLMConfig()
        self.client = instructor.from_openai(
            AsyncOpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )
        self.semaphore = asyncio.Semaphore(max_concurrency)

    @log_execution_time
    @observe(name="generic_pipeline.map_reduce_all_steps")
    async def map_reduce_all_steps(
        self,
        chunks: list[Chunk],
        instruction: str,
        notes_facts: list[str] | None = None,
    ) -> str:
        if not chunks:
            raise EmptyChunksError(
                "GenericMapReducePipeline.map_reduce_all_steps called with no chunks"
            )
        all_facts = await self._map(chunks, instruction)
        if not all_facts:
            if notes_facts:
                logger.warning(
                    "GenericMapReducePipeline: notes_facts provided but 0 fact "
                    "produced by the map phase — short-circuiting to empty "
                    "markdown (notes do not substitute for the transcript)."
                )
            record_empty_map_phase_event(
                section="generic_pipeline",
                chunk_count=len(chunks),
                notes_hint_present=bool(notes_facts),
            )
            return ""
        return await self._reduce(all_facts, instruction, notes_facts=notes_facts)

    async def map_one(self, chunk: Chunk, instruction: str) -> list[str]:
        async with self.semaphore:
            msg = (
                PromptTemplate(
                    template=MAP_PROMPT_TEMPLATE,
                    input_variables=["chunk_text", "instruction"],
                )
                .invoke({"chunk_text": chunk.text, "instruction": instruction})
                .to_string()
            )
            resp = await async_call_llm_with_structured_output(
                client=self.client,
                response_model=_MapResponse,
                user_message_content=msg,
            )
            return resp.facts

    @observe(name="generic_pipeline.map")
    async def _map(self, chunks: list[Chunk], instruction: str) -> list[str]:
        results = await asyncio.gather(*[self.map_one(c, instruction) for c in chunks])
        return [fact for sub in results for fact in sub]

    @observe(name="generic_pipeline.reduce")
    async def _reduce(
        self,
        facts: list[str],
        instruction: str,
        notes_facts: list[str] | None = None,
    ) -> str:
        msg = REDUCE_PROMPT_TEMPLATE.format(
            facts="\n- ".join(facts),
            instruction=instruction,
            notes_section=self._build_notes_facts_section(notes_facts),
        )
        resp = await async_call_llm_with_structured_output(
            client=self.client,
            response_model=_ReduceResponse,
            user_message_content=msg,
        )
        return resp.markdown

    def _build_notes_facts_section(self, notes_facts: list[str] | None) -> str:
        if not notes_facts:
            return ""
        bulleted = "- " + "\n- ".join(notes_facts)
        return NOTES_SECTION_TEMPLATE.format(notes_block=bulleted)
