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


class BaseInitThenRefine(ABC, Generic[T]):  # lint-ignore: no-docstring
    """Seed the result with the first chunk, then refine it iteratively chunk-by-chunk."""

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

    @log_execution_time
    @observe(name="init_then_refine")
    def init_then_refine(self, chunks: list[Chunk]) -> T:
        get_client().update_current_span(
            name=f"section_{self.section_name}_generation",
        )

        initial = self._initial_extract_from_chunk(chunks[0])
        refined = initial
        for chunk in chunks[1:]:
            refined = self._refine_with_chunk(current=refined, chunk_text=chunk.text)

        logger.debug("Final {} extract: {}", self.response_model.__name__, refined)
        return refined

    def _initial_extract_from_chunk(self, chunk: Chunk) -> T:
        prompt = PromptTemplate(
            template=self.initial_prompt_template,
            input_variables=["chunk_text"],
        )
        content = prompt.invoke({"chunk_text": chunk.text}).to_string()
        return cast(
            T,
            call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=self.response_model,
                user_message_content=content,
            ),
        )

    def _refine_with_chunk(self, current: T, chunk_text: str) -> T:
        prompt = PromptTemplate(
            template=self.refine_prompt_template,
            input_variables=["current_json", "chunk_text"],
        )
        content = prompt.invoke(
            {"current_json": current.model_dump_json(), "chunk_text": chunk_text}
        ).to_string()
        return cast(
            T,
            call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=self.response_model,
                user_message_content=content,
            ),
        )
