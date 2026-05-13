import asyncio
from abc import ABC, abstractmethod
from typing import Any

from mcr_generation.app.services.utils.input_chunker import Chunk


class MetadataCollector(ABC):
    """Wrap a legacy sync extractor behind a uniform async/markdown interface."""

    id: str
    description: str

    @abstractmethod
    def _extract(self, chunks: list[Chunk]) -> Any:
        """Run the underlying sync extractor and return its Pydantic output."""

    @abstractmethod
    def _to_markdown(self, result: Any) -> str:
        """Render the extractor's Pydantic output as markdown."""

    async def collect(self, chunks: list[Chunk]) -> str:
        result = await asyncio.to_thread(self._extract, chunks)
        return self._to_markdown(result)


METADATA_COLLECTORS: dict[str, MetadataCollector] = {}


def register(collector: MetadataCollector) -> None:
    if collector.id in METADATA_COLLECTORS:
        raise RuntimeError(f"Collector id already registered: {collector.id}")
    METADATA_COLLECTORS[collector.id] = collector
