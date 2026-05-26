"""Map-reduce generator base class.

Extract typed items from each chunk in parallel (map phase), then
consolidate them into a single content via one LLM reduce call.
Subclasses are purely declarative: 6 ``ClassVar``s and no method
overrides.
"""

import contextvars
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from typing import Any, ClassVar, Generic, Protocol, TypeVar, cast

import instructor
from langchain.prompts import PromptTemplate
from langfuse import get_client, observe
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel

from mcr_generation.app.configs.settings import LangfuseSettings, LLMConfig
from mcr_generation.app.exceptions.exceptions import AllChunksFailedError
from mcr_generation.app.schemas.base import Participant
from mcr_generation.app.services.notes.prompts import (
    NOTES_SECTION_TEMPLATE,
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


class _MappedItem(Protocol):
    """Structural typing contract for items produced by the map phase.

    No runtime inheritance: any Pydantic model exposing ``topic``,
    ``topic_confidence``, ``chunk_id`` and ``model_dump`` satisfies it.
    """

    topic: str
    topic_confidence: float
    chunk_id: int

    def model_dump(self, *, include: set[str] | None = ...) -> dict[str, Any]: ...


MappedT = TypeVar("MappedT", bound=_MappedItem)
ContentT = TypeVar("ContentT", bound=BaseModel)


class BaseMapReduce(ABC, Generic[MappedT, ContentT]):
    """Parallel map + single reduce against an LLM.

    Subclasses declare 7 ``ClassVar``s — see ``MapReduceTopics`` and
    ``MapReduceDetailedDiscussions`` for canonical examples.

    ``map_response_model`` is the LLM-facing wrapper class (the JSON
    schema sent to the LLM). ``item_model`` is the internal model used
    after the map phase; it must accept all fields of the LLM item plus
    a ``chunk_id`` keyword argument. Typically ``item_model`` is a
    subclass of the LLM item type adding only ``chunk_id``.

    ``items_field`` is dual-use: it names both the attribute on
    ``map_response_model`` that holds the per-chunk items list, and the
    placeholder in ``reduce_prompt_template`` that receives the
    aggregated items JSON.
    """

    max_workers: ClassVar[int] = 4

    section_name: ClassVar[str]
    map_response_model: ClassVar[type[BaseModel]]
    item_model: ClassVar[type[BaseModel]]
    content_model: ClassVar[type[BaseModel]]
    map_prompt_template: ClassVar[str]
    reduce_prompt_template: ClassVar[str]
    items_field: ClassVar[str]

    meeting_subject: str | None
    speaker_mapping: str | None
    _last_chunk_count: int | None = None

    def __init__(
        self,
        meeting_subject: str | None = None,
        participants: list[Participant] | None = None,
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
    @observe(name="map_reduce_all_steps")
    def map_reduce_all_steps(
        self,
        chunks: list[Chunk],
        notes_hint: ContentT | None = None,
    ) -> ContentT:
        get_client().update_current_span(
            name=f"section_{self.section_name}_generation",
        )
        self._last_chunk_count = len(chunks)
        successful, failed_chunk_ids = self._map_chunks_in_parallel(chunks)

        if failed_chunk_ids and not successful:
            raise AllChunksFailedError(
                f"All {len(chunks)} chunks failed in map phase: {failed_chunk_ids}"
            )

        logger.debug("Mapped items by chunk: {}", successful)
        all_items: list[MappedT] = [item for sublist in successful for item in sublist]
        return self._reduce(all_items, notes_hint=notes_hint)

    def _map_chunks_in_parallel(
        self, chunks: list[Chunk]
    ) -> tuple[list[list[MappedT]], list[int]]:
        successful: list[list[MappedT]] = []
        failed_chunk_ids: list[int] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                (
                    chunk.id,
                    executor.submit(
                        contextvars.copy_context().run,
                        self._map_extract,
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
                        section=self.section_name,
                        chunk_id=chunk_id,
                        exception_type=type(e).__name__,
                        exception_msg=str(e)[:500],
                    )
                    logger.warning("Chunk {} failed map phase: {}", chunk_id, e)

        return successful, failed_chunk_ids

    @observe(name="map_extract")
    def _map_extract(self, chunk: Chunk) -> list[MappedT]:
        get_client().update_current_span(name=f"section_{self.section_name}_map")

        prompt = PromptTemplate(
            template=self.map_prompt_template,
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
            response_model=self.map_response_model,
            user_message_content=content,
        )
        llm_items = getattr(resp, self.items_field)

        items = cast(
            list[MappedT],
            [
                self.item_model(**llm_item.model_dump(), chunk_id=chunk.id)
                for llm_item in llm_items
            ],
        )

        self._record_low_confidence_items(items, chunk.id)
        return items

    @observe(name="reduce")
    def _reduce(
        self,
        all_items: list[MappedT],
        notes_hint: ContentT | None = None,
    ) -> ContentT:
        get_client().update_current_span(name=f"section_{self.section_name}_reduce")

        if not all_items:
            if notes_hint is not None:
                logger.warning(
                    "Section {}: notes hint provided but 0 item produced by the map "
                    "phase. Short-circuiting to empty content (notes do not "
                    "substitute for the transcript).",
                    self.section_name,
                )
            record_empty_map_phase_event(
                section=self.section_name,
                chunk_count=self._last_chunk_count,
            )
            return cast(ContentT, self.content_model())

        items_input = [item.model_dump() for item in all_items]
        reduce_message = self.reduce_prompt_template.format(
            **{self.items_field: items_input},
            meeting_subject=self.meeting_subject or "Inconnu",
            speaker_mapping=self.speaker_mapping or "Non fourni",
            notes_section=self._build_notes_section(notes_hint),
        )

        return cast(
            ContentT,
            call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=self.content_model,
                user_message_content=reduce_message,
            ),
        )

    def _build_notes_section(self, notes_hint: ContentT | None) -> str:
        if notes_hint is None:
            return ""
        return NOTES_SECTION_TEMPLATE.format(
            notes_block=notes_hint.model_dump_json(),
        )

    def _record_low_confidence_items(self, items: list[MappedT], chunk_id: int) -> None:
        threshold = langfuse_settings.LOW_CONFIDENCE_THRESHOLD
        low = [
            item.model_dump(include={"topic", "topic_confidence"})
            for item in items
            if item.topic_confidence < threshold
        ]
        if low:
            record_low_confidence_items_event(
                section=self.section_name,
                chunk_id=chunk_id,
                threshold=threshold,
                items=low,
            )
