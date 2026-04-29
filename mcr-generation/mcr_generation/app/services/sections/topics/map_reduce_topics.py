"""Module for extracting and consolidating topics with a topic from meeting transcripts"""

import contextvars
from concurrent.futures import ThreadPoolExecutor

import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from loguru import logger
from openai import OpenAI

from mcr_generation.app.configs.settings import LangfuseSettings, LLMConfig
from mcr_generation.app.exceptions.exceptions import AllChunksFailedError
from mcr_generation.app.schemas.base import Participant
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
from mcr_generation.app.utils.langfuse_observability import (
    record_chunk_map_failed_event,
    record_empty_map_phase_event,
    record_low_confidence_items_event,
)

langfuse_settings = LangfuseSettings()


class MapReduceTopics:
    max_workers: int = 4
    meeting_subject: str | None
    speaker_mapping: str | None
    _last_chunk_count: int | None = None

    def __init__(
        self,
        meeting_subject: str | None = None,
        participants: list[Participant] = [],
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
        self.speaker_mapping = str(participants) if participants else None

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
        self._last_chunk_count = len(chunks)
        successful: list[list[MappedTopic]] = []
        failed_chunk_ids: list[int] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                (
                    chunk.id,
                    executor.submit(
                        contextvars.copy_context().run,
                        self.map_extract_topics,
                        chunk,
                    ),
                )
                for chunk in chunks
            ]
            for chunk_id, fut in futures:
                try:
                    successful.append(fut.result())
                except Exception as e:
                    failed_chunk_ids.append(chunk_id)
                    record_chunk_map_failed_event(
                        section="topics",
                        chunk_id=chunk_id,
                        exception_type=type(e).__name__,
                        exception_msg=str(e)[:500],
                    )
                    logger.warning("Chunk {} failed map phase: {}", chunk_id, e)

        if failed_chunk_ids and not successful:
            raise AllChunksFailedError(
                f"All {len(chunks)} chunks failed in map phase: {failed_chunk_ids}"
            )

        logger.debug("Mapped topics by chunk: {}", successful)
        all_topics = [topic for sublist in successful for topic in sublist]
        return self.reduce_topics_into_content(all_topics)

    @observe(name="section_content_reduce")
    def reduce_topics_into_content(self, all_topics: list[MappedTopic]) -> Content:
        """
        Deduplicate and merge related topics using the LLM.

        Args:
            all_topics (List[MappedTopic]): List of MappedTopic objects extracted from chunks.

        Returns:
            Content: Deduplicated and consolidated list of topics.
        """
        if not all_topics:
            record_empty_map_phase_event(
                section="topics",
                chunk_count=self._last_chunk_count,
            )
            return Content(topics=[], next_steps=[])

        topics_input = [d.model_dump() for d in all_topics]

        reduce_message = REDUCE_PROMPT_TEMPLATE.format(
            topics=topics_input,
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
    def map_extract_topics(self, chunk: Chunk) -> list[MappedTopic]:
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
            response_model=MappedTopics,
            user_message_content=content,
        )
        topics = resp.topics

        threshold = langfuse_settings.LOW_CONFIDENCE_THRESHOLD
        low = [
            {"topic": t.topic, "confidence": t.topic_confidence}
            for t in topics
            if t.topic_confidence < threshold
        ]
        if low:
            record_low_confidence_items_event(
                section="topics",
                chunk_id=chunk.id,
                threshold=threshold,
                items=low,
            )

        return topics
