"""Module for extracting and consolidating detailed discussions from meeting transcripts"""

import contextvars
from concurrent.futures import ThreadPoolExecutor

import instructor
from langchain.prompts import PromptTemplate
from langfuse import get_client, observe
from loguru import logger
from openai import OpenAI

from mcr_generation.app.configs.settings import LangfuseSettings, LLMConfig
from mcr_generation.app.exceptions.exceptions import AllChunksFailedError
from mcr_generation.app.schemas.base import Participant
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
    @observe(name="section_content_generation")
    def map_reduce_all_steps(self, chunks: list[Chunk]) -> Content:
        self._last_chunk_count = len(chunks)
        successful: list[list[MappedDetailedDiscussion]] = []
        failed_chunk_ids: list[int] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                (
                    chunk.id,
                    executor.submit(
                        contextvars.copy_context().run,
                        self.map_extract_detailed_discussions,
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
                    get_client().create_event(
                        name="chunk_map_failed",
                        level="ERROR",
                        metadata={
                            "section": "detailed_discussions",
                            "chunk_id": chunk_id,
                            "exception_type": type(e).__name__,
                            "exception_msg": str(e)[:500],
                        },
                    )
                    logger.warning("Chunk {} failed map phase: {}", chunk_id, e)

        if failed_chunk_ids and not successful:
            raise AllChunksFailedError(
                f"All {len(chunks)} chunks failed in map phase: {failed_chunk_ids}"
            )

        logger.debug("Mapped detailed discussions by chunk: {}", successful)
        all_discussions = [
            discussion for sublist in successful for discussion in sublist
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
            get_client().create_event(
                name="empty_map_phase",
                level="WARNING",
                metadata={
                    "section": "detailed_discussions",
                    "chunk_count": getattr(self, "_last_chunk_count", None),
                },
            )
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

        threshold = LangfuseSettings().LOW_CONFIDENCE_THRESHOLD
        low = [
            {"topic": d.topic, "confidence": d.topic_confidence}
            for d in discussions
            if d.topic_confidence < threshold
        ]
        if low:
            get_client().create_event(
                name="low_confidence_detailed_discussions",
                level="WARNING",
                metadata={
                    "chunk_id": chunk.id,
                    "threshold": threshold,
                    "items": low,
                },
            )

        return discussions
