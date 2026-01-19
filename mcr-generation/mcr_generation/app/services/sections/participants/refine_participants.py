from typing import Optional

import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from loguru import logger
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import Participants
from mcr_generation.app.services.sections.participants.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)
from mcr_generation.app.utils.function_execution_timer import log_execution_time


class RefineParticipants:
    """
    Seeds with the first chunk, then refines with subsequent chunks to extract participants.
    """

    max_chunks: Optional[int] = None

    def __init__(
        self,
    ) -> None:
        self.llm_config = LLMConfig()

        self.client_instructor = instructor.from_openai(
            OpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    @log_execution_time
    @observe(name="section_participants_generation")
    def init_then_refine(self, chunks: list[Chunk]) -> Participants:
        initial_extract = self._initial_extract_from_chunk(chunks[0])

        logger.debug("Initial extract: {}", initial_extract)

        refined_extract = initial_extract
        for chunk in chunks[1:]:
            refined_extract = self._refine_with_chunk(
                current=refined_extract, chunk_text=chunk.text
            )
            logger.debug("Refined extract so far: {}", refined_extract)

        logger.debug("Final refined extract: {}", refined_extract)

        return refined_extract

    def _initial_extract_from_chunk(self, chunk: Chunk) -> Participants:
        prompt = PromptTemplate(
            template=INITIAL_PROMPT_TEMPLATE,
            input_variables=["chunk_text"],
        )

        content = prompt.invoke({"chunk_text": chunk.text}).to_string()

        logger.debug(
            "Initial extract prompt: {}",
            content,
        )
        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=Participants,
            user_message_content=content,
        )
        logger.debug("Initial response: {}", resp)
        return resp

    def _refine_with_chunk(
        self, current: Participants, chunk_text: str
    ) -> Participants:
        current_json = current.model_dump_json()

        prompt = PromptTemplate(
            template=REFINE_PROMPT_TEMPLATE,
            input_variables=["current_json", "chunk_text"],
        )

        content = prompt.invoke(
            {
                "current_json": current_json,
                "chunk_text": chunk_text,
            }
        ).to_string()

        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=Participants,
            user_message_content=content,
        )
        logger.debug("Refined response: {}", resp)
        return resp
