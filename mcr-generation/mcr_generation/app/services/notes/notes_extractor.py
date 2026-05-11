import asyncio
from collections.abc import Awaitable

import instructor
from langfuse import observe
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from mcr_generation.app.configs.settings import ChunkingConfig, LLMConfig
from mcr_generation.app.schemas.base import Intent, NextMeeting
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.notes.prompts import (
    EXTRACT_DISCUSSIONS_HINT_PROMPT_TEMPLATE,
    EXTRACT_INTENT_PROMPT_TEMPLATE,
    EXTRACT_NEXT_MEETING_PROMPT_TEMPLATE,
    EXTRACT_TOPICS_HINT_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.detailed_discussions.types import (
    DiscussionsContent,
)
from mcr_generation.app.services.sections.topics.types import TopicsContent
from mcr_generation.app.services.utils.llm_helpers import (
    async_call_llm_with_structured_output,
)
from mcr_generation.app.utils.function_execution_timer import log_execution_time
from mcr_generation.app.utils.langfuse_observability import (
    record_notes_extraction_failed_event,
    record_notes_truncated_event,
)


class ExtractedNotes(BaseModel):
    intent: Intent | None = None
    next_meeting: NextMeeting | None = None
    topics: TopicsContent | None = None
    discussions: DiscussionsContent | None = None


class NotesExtractor:
    max_workers: int = 4

    def __init__(self) -> None:
        self.llm_config = LLMConfig()
        self.chunking_config = ChunkingConfig()
        self.client_instructor = instructor.from_openai(
            AsyncOpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )
        self._semaphore = asyncio.Semaphore(self.max_workers)

    @log_execution_time
    @observe(name="notes_extraction")
    async def extract_all(
        self,
        notes_content: str,
        report_type: ReportTypes,
    ) -> ExtractedNotes:
        notes_content = self._truncate_if_too_long(notes_content)

        tasks: dict[str, Awaitable[BaseModel]] = {
            "intent": self.extract_intent(notes_content),
            "next_meeting": self.extract_next_meeting(notes_content),
        }
        match report_type:
            case ReportTypes.DECISION_RECORD:
                tasks["topics"] = self.extract_topics_hint(notes_content)
            case ReportTypes.DETAILED_SYNTHESIS:
                tasks["discussions"] = self.extract_discussions_hint(notes_content)

        keys = list(tasks.keys())
        raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results: dict[str, BaseModel | None] = {}
        for key, value in zip(keys, raw_results, strict=True):
            if isinstance(value, BaseException):
                record_notes_extraction_failed_event(
                    theme=key,
                    exception_type=type(value).__name__,
                    exception_msg=str(value)[:500],
                )
                results[key] = None
            else:
                results[key] = value

        return ExtractedNotes(
            intent=results.get("intent"),
            next_meeting=results.get("next_meeting"),
            topics=results.get("topics"),
            discussions=results.get("discussions"),
        )

    @observe(name="notes_extract_intent")
    async def extract_intent(self, notes_content: str) -> Intent:
        prompt = EXTRACT_INTENT_PROMPT_TEMPLATE.format(notes_content=notes_content)
        async with self._semaphore:
            return await async_call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=Intent,
                user_message_content=prompt,
            )

    @observe(name="notes_extract_next_meeting")
    async def extract_next_meeting(self, notes_content: str) -> NextMeeting:
        prompt = EXTRACT_NEXT_MEETING_PROMPT_TEMPLATE.format(
            notes_content=notes_content
        )
        async with self._semaphore:
            return await async_call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=NextMeeting,
                user_message_content=prompt,
            )

    @observe(name="notes_extract_topics_hint")
    async def extract_topics_hint(self, notes_content: str) -> TopicsContent:
        prompt = EXTRACT_TOPICS_HINT_PROMPT_TEMPLATE.format(notes_content=notes_content)
        async with self._semaphore:
            return await async_call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=TopicsContent,
                user_message_content=prompt,
            )

    @observe(name="notes_extract_discussions_hint")
    async def extract_discussions_hint(self, notes_content: str) -> DiscussionsContent:
        prompt = EXTRACT_DISCUSSIONS_HINT_PROMPT_TEMPLATE.format(
            notes_content=notes_content
        )
        async with self._semaphore:
            return await async_call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=DiscussionsContent,
                user_message_content=prompt,
            )

    def _truncate_if_too_long(self, notes_content: str) -> str:
        max_len = self.chunking_config.CHUNK_SIZE
        if len(notes_content) <= max_len:
            return notes_content
        logger.warning(
            "Notes content too long ({} chars > CHUNK_SIZE={}), truncating.",
            len(notes_content),
            max_len,
        )
        record_notes_truncated_event(
            original_length=len(notes_content),
            truncated_length=max_len,
        )
        return notes_content[:max_len]


def extract_notes(
    notes_content: str | None,
    report_type: ReportTypes,
) -> ExtractedNotes | None:
    if not notes_content or not notes_content.strip():
        logger.debug("Notes extraction skipped: no notes content")
        return None

    extracted_notes = asyncio.run(
        NotesExtractor().extract_all(notes_content, report_type=report_type)
    )
    logger.debug("Notes extraction done")
    return extracted_notes
