from abc import ABC, abstractmethod

import instructor
from langchain.schema import Document
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
        self.separator: str

    def _chunk_text(self, text: str) -> list[Chunk]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_config.CHUNK_SIZE,
            chunk_overlap=self.chunk_config.CHUNK_OVERLAP,
        )

        chunks = text_splitter.split_text(text)
        chunked_documents = [Document(page_content=chunk) for chunk in chunks]

        logger.debug("Nb of chunked documents: {}", len(chunked_documents))

        chunks_with_ids = [
            Chunk(id=idx, text=doc.page_content)
            for idx, doc in enumerate(chunked_documents)
        ]

        logger.debug("chunks_with_ids {}", chunks_with_ids)

        return chunks_with_ids

    @abstractmethod
    def _format_segments_for_llm(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> str: ...
