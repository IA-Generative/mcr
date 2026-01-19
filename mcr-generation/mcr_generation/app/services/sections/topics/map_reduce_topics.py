"""Module for extracting and consolidating topics with a topic from meeting transcripts"""

from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from loguru import logger
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import Participants
from mcr_generation.app.services.sections.topics.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.topics.types import (
    Content,
    MappedTopic,
    MappedTopics,
)
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)
from mcr_generation.app.utils.function_execution_timer import log_execution_time


class MapReduceTopics:
    max_workers: int = 4
    meeting_subject: Optional[str]
    speaker_mapping: Optional[str]

    def __init__(
        self,
        meeting_subject: Optional[str] = None,
        speaker_mapping: Optional[Participants] = None,
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

    # rename into: process section -> generate section ?
    @log_execution_time
    @observe(name="section_content_generation")
    def map_reduce_all_steps(self, chunks: list[Chunk]) -> Content:
        content = self.process_transcript_parallel(
            chunks=chunks, max_workers=self.max_workers
        )

        return content

    def process_transcript_parallel(
        self, chunks: list[Chunk], max_workers: int = 4
    ) -> Content:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            topics_by_chunk = list(executor.map(self.map_extract_topics, chunks))
            logger.debug("Mapped topics by chunk: {}", topics_by_chunk)
            all_topics = [topic for sublist in topics_by_chunk for topic in sublist]
        return self.reduce_topics_into_content(all_topics)

    @observe(name="section_content_reduce")
    def reduce_topics_into_content(self, all_topics: List[MappedTopic]) -> Content:
        """
        Deduplicate and merge related topics using the LLM.

        Args:
            all_topics (List[MappedTopic]): List of MappedTopic objects extracted from chunks.

        Returns:
            Content: Deduplicated and consolidated list of topics.
        """
        if not all_topics:
            return Content(topics=[], next_steps=[])

        topics_input = [d.model_dump() for d in all_topics]

        reduce_message = REDUCE_PROMPT_TEMPLATE.format(
            topics=topics_input,
            meeting_subject=self.meeting_subject,
            speaker_mapping=self.speaker_mapping,
        )

        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=Content,
            user_message_content=reduce_message,
        )

        return resp

    @observe(name="section_content_map")
    def map_extract_topics(self, chunk: Chunk) -> List[MappedTopic]:
        prompt = PromptTemplate(
            template=MAP_PROMPT_TEMPLATE,
            input_variables=["chunk_text", "meeting_subject", "speaker_mapping"],
        )

        content = prompt.invoke(
            {
                "chunk_text": chunk.text,
                "meeting_subject": self.meeting_subject,
                "speaker_mapping": self.speaker_mapping,
            }
        ).to_string()
        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=MappedTopics,
            user_message_content=content,
        )
        topics = resp.topics

        return topics
