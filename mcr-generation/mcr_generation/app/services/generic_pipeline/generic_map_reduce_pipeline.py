"""Generic async map-reduce pipeline producing markdown.

The instruction string is injected verbatim into both map and reduce prompts.
Callers (rewriter / orchestrator) are responsible for crafting the instruction.
"""

import asyncio

import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.exceptions.exceptions import EmptyChunksError
from mcr_generation.app.services.generic_pipeline.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
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


class _ReduceResponse(BaseModel):
    markdown: str


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
    async def map_reduce_all_steps(self, chunks: list[Chunk], instruction: str) -> str:
        if not chunks:
            raise EmptyChunksError(
                "GenericMapReducePipeline.map_reduce_all_steps called with no chunks"
            )
        all_facts = await self._map(chunks, instruction)
        if not all_facts:
            record_empty_map_phase_event(
                section="generic_pipeline",
                chunk_count=len(chunks),
            )
            return ""
        return await self._reduce(all_facts, instruction)

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
    async def _reduce(self, facts: list[str], instruction: str) -> str:
        msg = REDUCE_PROMPT_TEMPLATE.format(
            facts="\n- ".join(facts),
            instruction=instruction,
        )
        resp = await async_call_llm_with_structured_output(
            client=self.client,
            response_model=_ReduceResponse,
            user_message_content=msg,
        )
        return resp.markdown
