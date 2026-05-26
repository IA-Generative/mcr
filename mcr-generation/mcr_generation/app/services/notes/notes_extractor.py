import asyncio
from collections.abc import Awaitable, Iterable
from typing import Any

import instructor
from langfuse import observe
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from mcr_generation.app.configs.settings import ChunkingConfig, LLMConfig
from mcr_generation.app.schemas.base import Intent, NextMeeting
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.prompts import (
    EXTRACT_CUSTOM_FACTS_PROMPT_TEMPLATE,
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


class _NotesFacts(BaseModel):
    facts: list[str] = Field(default_factory=list)


class ExtractedNotes(BaseModel):
    intent: Intent | None = None
    next_meeting: NextMeeting | None = None
    topics: TopicsContent | None = None
    discussions: DiscussionsContent | None = None
    custom_section_facts: dict[str, list[str]] | None = None


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
        facets: Iterable[NotesFacet] = (),
        custom_instructions: Iterable[str] | None = None,
    ) -> ExtractedNotes:
        facets_set = frozenset(facets)
        instructions_list: list[str] = (
            list(custom_instructions) if custom_instructions else []
        )

        if not facets_set and not instructions_list:
            return ExtractedNotes()

        notes_content = self._truncate_if_too_long(notes_content)

        facet_tasks: dict[NotesFacet, Awaitable[BaseModel]] = {}
        for facet in facets_set:
            match facet:
                case NotesFacet.INTENT:
                    facet_tasks[facet] = self.extract_intent(notes_content)
                case NotesFacet.NEXT_MEETING:
                    facet_tasks[facet] = self.extract_next_meeting(notes_content)
                case NotesFacet.TOPICS:
                    facet_tasks[facet] = self.extract_topics_hint(notes_content)
                case NotesFacet.DISCUSSIONS:
                    facet_tasks[facet] = self.extract_discussions_hint(notes_content)

        facet_keys = list(facet_tasks.keys())
        coros: list[Awaitable[Any]] = list(facet_tasks.values())
        for instruction in instructions_list:
            coros.append(self._extract_custom_facts(notes_content, instruction))

        raw_results = await asyncio.gather(*coros, return_exceptions=True)

        facet_results = raw_results[: len(facet_keys)]
        custom_results = raw_results[len(facet_keys) :]

        facet_values: dict[NotesFacet, BaseModel | None] = {}
        for key, value in zip(facet_keys, facet_results, strict=True):
            if isinstance(value, BaseException):
                record_notes_extraction_failed_event(
                    theme=key,
                    exception_type=type(value).__name__,
                    exception_msg=str(value)[:500],
                )
                facet_values[key] = None
            else:
                facet_values[key] = value

        custom_facts: dict[str, list[str]] = {}
        for instruction, value in zip(instructions_list, custom_results, strict=True):
            if isinstance(value, BaseException):
                custom_facts[instruction] = []
            else:
                custom_facts[instruction] = value

        return ExtractedNotes(
            intent=facet_values.get(NotesFacet.INTENT),
            next_meeting=facet_values.get(NotesFacet.NEXT_MEETING),
            topics=facet_values.get(NotesFacet.TOPICS),
            discussions=facet_values.get(NotesFacet.DISCUSSIONS),
            custom_section_facts=custom_facts if instructions_list else None,
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

    @observe(name="notes_extract_custom_facts")
    async def _extract_custom_facts(
        self, notes_content: str, instruction: str
    ) -> list[str]:
        prompt = EXTRACT_CUSTOM_FACTS_PROMPT_TEMPLATE.format(
            instruction=instruction,
            notes_content=notes_content,
        )
        try:
            async with self._semaphore:
                response = await async_call_llm_with_structured_output(
                    client=self.client_instructor,
                    response_model=_NotesFacts,
                    user_message_content=prompt,
                )
        except Exception as e:
            record_notes_extraction_failed_event(
                theme="custom_facts",
                exception_type=type(e).__name__,
                exception_msg=str(e)[:500],
            )
            return []
        return response.facts

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
