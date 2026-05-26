import asyncio
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Literal, get_args

from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.utils.input_chunker import Chunk

CollectorId = Literal[
    "title",
    "participants",
    "topics",
    "detailed_discussions",
    "next_meeting",
]

COLLECTOR_IDS: frozenset[CollectorId] = frozenset(get_args(CollectorId))


class MetadataCollector(ABC):
    """Wrap a legacy sync extractor behind a uniform async/markdown interface."""

    id: CollectorId
    description: str
    notes_facets: ClassVar[frozenset[NotesFacet]] = frozenset()

    @abstractmethod
    def _extract(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> Any:
        """Run the underlying sync extractor and return its Pydantic output."""

    @abstractmethod
    def _to_markdown(self, result: Any) -> str:
        """Render the extractor's Pydantic output as markdown."""

    async def collect(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> str:
        result = await asyncio.to_thread(self._extract, chunks, extracted_notes)
        return self._to_markdown(result)


METADATA_COLLECTORS: dict[CollectorId, MetadataCollector] = {}


def register(collector: MetadataCollector) -> None:
    if collector.id not in COLLECTOR_IDS:
        raise RuntimeError(f"Collector id not in CollectorId Literal: {collector.id!r}")
    if collector.id in METADATA_COLLECTORS:
        raise RuntimeError(f"Collector id already registered: {collector.id}")
    METADATA_COLLECTORS[collector.id] = collector
