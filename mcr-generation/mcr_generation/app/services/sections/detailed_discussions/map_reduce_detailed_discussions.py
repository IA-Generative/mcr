"""Module for extracting and consolidating detailed discussions from meeting transcripts"""

from concurrent.futures import ThreadPoolExecutor

import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from loguru import logger
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import Participants
from mcr_generation.app.services.sections.detailed_discussions.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.detailed_discussions.types import (
    Content,
    MappedDetailedDiscussion,
    MappedDetailedDiscussions,
)
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)
from mcr_generation.app.utils.function_execution_timer import log_execution_time


class MapReduceDetailedDiscussions:
    max_workers: int = 4
    meeting_subject: str | None
    speaker_mapping: str | None

    def __init__(
        self,
        meeting_subject: str | None = None,
        speaker_mapping: Participants | None = None,
    ) -> None:
        self.llm_config = LLMConfig()
        self.client_instructor = instructor.from_openai(
            OpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )
        self.meeting_subject = meeting_subject
        self.speaker_mapping = str(speaker_mapping) if speaker_mapping else None

    @log_execution_time
    @observe(name="section_content_generation")
    def map_reduce_all_steps(self, chunks: list[Chunk]) -> Content:
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            discussions_by_chunk = list(
                executor.map(self.map_extract_detailed_discussions, chunks)
            )
            logger.debug(
                "Mapped detailed discussions by chunk: {}", discussions_by_chunk
            )
            all_discussions = [
                discussion for sublist in discussions_by_chunk for discussion in sublist
            ]
        return self.reduce_discussions_into_content(all_discussions)

    @observe(name="section_content_reduce")
    def reduce_discussions_into_content(
        self, all_discussions: list[MappedDetailedDiscussion]
    ) -> Content:
        """
        Deduplicate and merge related detailed discussions using the LLM.

        Args:
            all_discussions (list[MappedDetailedDiscussion]): List of MappedDetailedDiscussion
                objects extracted from chunks.

        Returns:
            Content: Deduplicated and consolidated list of detailed discussions.
        """
        if not all_discussions:
            return Content(detailed_discussions=[])

        discussions_input = [d.model_dump() for d in all_discussions]

        reduce_message = REDUCE_PROMPT_TEMPLATE.format(
            detailed_discussions=discussions_input,
            meeting_subject=self.meeting_subject or "Inconnu",
            speaker_mapping=self.speaker_mapping or "Non fourni",
        )

        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=Content,
            user_message_content=reduce_message,
        )

        return resp

    @observe(name="section_content_map")
    def map_extract_detailed_discussions(
        self, chunk: Chunk
    ) -> list[MappedDetailedDiscussion]:
        prompt = PromptTemplate(
            template=MAP_PROMPT_TEMPLATE,
            input_variables=["chunk_text", "meeting_subject", "speaker_mapping"],
        )

        content = prompt.invoke(
            {
                "chunk_text": chunk.text,
                "meeting_subject": self.meeting_subject or "Inconnu",
                "speaker_mapping": self.speaker_mapping or "Non fourni",
            }
        ).to_string()

        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=MappedDetailedDiscussions,
            user_message_content=content,
        )

        discussions = resp.detailed_discussions
        for discussion in discussions:
            discussion.chunk_id = chunk.id
        return discussions
