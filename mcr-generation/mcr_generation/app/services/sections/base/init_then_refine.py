from abc import ABC
from typing import ClassVar, Generic, TypeVar, cast

import instructor
from langchain.prompts import PromptTemplate
from langfuse import get_client, observe
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)
from mcr_generation.app.utils.function_execution_timer import log_execution_time

T = TypeVar("T", bound=BaseModel)


class BaseInitThenRefine(ABC, Generic[T]):
    """Seed the result, then refine it iteratively chunk-by-chunk.

    The seed comes from ``init_hint`` when provided (all chunks are then used for
    refinement); otherwise it is extracted from the first chunk and the remaining
    chunks are used for refinement.

    Subclasses may feed extra reference text to every prompt by overriding
    ``_extra_prompt_vars``: the returned mapping is substituted into matching
    ``{placeholders}`` of both prompt templates. Refiners that don't override it
    keep single-variable prompts untouched.
    """

    response_model: ClassVar[type[BaseModel]]
    initial_prompt_template: ClassVar[str]
    refine_prompt_template: ClassVar[str]
    section_name: ClassVar[str]

    def __init__(self) -> None:
        self.llm_config = LLMConfig()
        self.client_instructor = instructor.from_openai(
            OpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    def _extra_prompt_vars(self) -> dict[str, str]:
        """Extra variables merged into both prompt templates. Empty by default."""
        return {}

    @log_execution_time
    @observe(name="init_then_refine")
    def init_then_refine(
        self,
        chunks: list[Chunk],
        init_hint: T | None = None,
    ) -> T:
        get_client().update_current_span(
            name=f"section_{self.section_name}_generation",
        )

        if init_hint is not None:
            refined, chunks_to_refine = init_hint, chunks
        else:
            refined, chunks_to_refine = (
                self._initial_extract_from_chunk(chunks[0]),
                chunks[1:],
            )

        for chunk in chunks_to_refine:
            refined = self._refine_with_chunk(current=refined, chunk_text=chunk.text)

        logger.debug("Final {} extract: {}", self.response_model.__name__, refined)
        return refined

    def _initial_extract_from_chunk(self, chunk: Chunk) -> T:
        prompt = PromptTemplate.from_template(self.initial_prompt_template)
        content = prompt.invoke(
            {"chunk_text": chunk.text, **self._extra_prompt_vars()}
        ).to_string()
        return cast(
            T,
            call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=self.response_model,
                user_message_content=content,
            ),
        )

    def _refine_with_chunk(self, current: T, chunk_text: str) -> T:
        prompt = PromptTemplate.from_template(self.refine_prompt_template)
        content = prompt.invoke(
            {
                "current_json": current.model_dump_json(),
                "chunk_text": chunk_text,
                **self._extra_prompt_vars(),
            }
        ).to_string()
        return cast(
            T,
            call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=self.response_model,
                user_message_content=content,
            ),
        )
