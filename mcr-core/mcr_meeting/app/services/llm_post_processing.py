from abc import ABC, abstractmethod

import instructor
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel

from mcr_meeting.app.configs.base import ChunkingConfig, LLMSettings
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


class Chunk(BaseModel):
    id: int
    text: str


class LLMPostProcessing(ABC):
    def __init__(self) -> None:
        self.settings = LLMSettings()
        self.chunk_config = ChunkingConfig()
        self.client = instructor.from_openai(
            OpenAI(
                base_url=self.settings.LLM_HUB_API_URL,
                api_key=self.settings.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    def _chunk_text(self, text: str, *, chunk_overlap: int = 0) -> list[Chunk]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_config.CHUNK_SIZE,
            chunk_overlap=chunk_overlap,
        )

        chunked_text = text_splitter.split_text(text)

        logger.debug("Nb of chunked documents: {}", len(chunked_text))

        chunks = [Chunk(id=idx, text=text) for idx, text in enumerate(chunked_text)]

        return chunks

    @abstractmethod
    def _format_segments_for_llm(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> str: ...
