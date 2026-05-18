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
from mcr_generation.app.services.sections.base.prompts import (
    NOTES_SECTION_TEMPLATE,
)
from mcr_generation.app.services.sections.topics.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.topics.types import (
    MappedTopic,
    MappedTopics,
    TopicsContent,
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

    @log_execution_time
    @observe(name="section_topics_generation")
    def map_reduce_all_steps(
        self,
        chunks: list[Chunk],
        notes_hint: TopicsContent | None = None,
    ) -> TopicsContent:
        self._last_chunk_count = len(chunks)
        successful, failed_chunk_ids = self._map_chunks_in_parallel(chunks)

        if failed_chunk_ids and not successful:
            raise AllChunksFailedError(
                f"All {len(chunks)} chunks failed in map phase: {failed_chunk_ids}"
            )

        logger.debug("Mapped topics by chunk: {}", successful)
        all_topics = [topic for sublist in successful for topic in sublist]
        return self.reduce_topics_into_content(all_topics, notes_hint=notes_hint)

    def _map_chunks_in_parallel(
        self, chunks: list[Chunk]
    ) -> tuple[list[list[MappedTopic]], list[int]]:
        successful: list[list[MappedTopic]] = []
        failed_chunk_ids: list[int] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
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

        return successful, failed_chunk_ids

    @observe(name="section_topics_reduce")
    def reduce_topics_into_content(
        self,
        all_topics: list[MappedTopic],
        notes_hint: TopicsContent | None = None,
    ) -> TopicsContent:
        """
        Deduplicate and merge related topics using the LLM.

        Args:
            all_topics (List[MappedTopic]): List of MappedTopic objects extracted from chunks.
            notes_hint (TopicsContent | None): Optional topics extracted from the meeting
                notes, used as a human-priority signal during consolidation.

        Returns:
            TopicsContent: Deduplicated and consolidated list of topics.
        """
        if not all_topics:
            if notes_hint is not None:
                logger.warning(
                    "Section topics: notes hint provided but 0 item produced by the "
                    "map phase. Short-circuiting to empty TopicsContent (notes do "
                    "not substitute for the transcript)."
                )
            record_empty_map_phase_event(
                section="topics",
                chunk_count=self._last_chunk_count,
            )
            return TopicsContent(topics=[], next_steps=[])

        topics_input = [d.model_dump() for d in all_topics]

        reduce_message = REDUCE_PROMPT_TEMPLATE.format(
            topics=topics_input,
            meeting_subject=self.meeting_subject or "Inconnu",
            speaker_mapping=self.speaker_mapping or "Non fourni",
            notes_section=self._build_notes_section(notes_hint),
        )

        resp = call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=TopicsContent,
            user_message_content=reduce_message,
        )

        return resp

    def _build_notes_section(self, notes_hint: TopicsContent | None) -> str:
        if notes_hint is None:
            return ""
        return NOTES_SECTION_TEMPLATE.format(
            notes_hint_json=notes_hint.model_dump_json(),
        )

    @observe(name="section_topics_map")
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

        self._record_low_confidence_items(topics, chunk.id)

        return topics

    def _record_low_confidence_items(
        self, topics: list[MappedTopic], chunk_id: int
    ) -> None:
        threshold = langfuse_settings.LOW_CONFIDENCE_THRESHOLD
        low = [
            t.model_dump(include={"topic", "topic_confidence"})
            for t in topics
            if t.topic_confidence < threshold
        ]
        if low:
            record_low_confidence_items_event(
                section="topics",
                chunk_id=chunk_id,
                threshold=threshold,
                items=low,
            )
