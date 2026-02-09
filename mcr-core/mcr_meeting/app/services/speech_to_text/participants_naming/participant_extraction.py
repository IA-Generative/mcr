from typing import List, Optional

import instructor
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from mcr_meeting.app.configs.base import ChunkingConfig, LLMSettings
from mcr_meeting.app.services.speech_to_text.participants_naming.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)


class Participant(BaseModel):
    speaker_id: str = Field(
        description="Identifiant unique du locuteur dans la transcription ex: LOCUTEUR_03.",
    )
    name: Optional[str] = Field(
        None,
        description="Prenom et/ou nom déduit pour le locuteur à partir des interactions dans la transcription. Ex: 'Jean' ou 'Jean Dupont'.",
    )
    role: Optional[str] = Field(
        None,
        description="Fonction/rôle si mentionné ou déduit (ex. PO, Tech Lead, Directeur financier).",
    )
    confidence: Optional[float] = Field(
        ge=0.0,
        le=1.0,
        description="Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain du nom associé locuteur.",
    )
    association_justification: Optional[str] = Field(
        description=(
            "Identification explicite ou déduction par contexte ayant permis d'associer ce nom/rôle au locuteur avec l'id."
        ),
    )


class Chunk(BaseModel):
    id: int
    text: str


class ParticipantExtraction:
    def __init__(self):
        self.settings = LLMSettings()
        self.chunk_config = ChunkingConfig()
        self.client = instructor.from_openai(
            OpenAI(
                base_url=self.settings.LLM_HUB_API_URL,
                api_key=self.settings.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    def extract(self, text: str) -> List[Participant]:
        chunks = self._chunk_text(text)

        # Seed with first chunk
        participants = self._initial_extract(chunks[0])

        # Refine with subsequent chunks
        for chunk in chunks[1:]:
            participants = self._refine(participants, chunk)

        return participants

    def _initial_extract(self, chunk_text: str) -> List[Participant]:
        # Use INITIAL_PROMPT_TEMPLATE
        return self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=List[Participant],
            messages=[
                {
                    "role": "user",
                    "content": INITIAL_PROMPT_TEMPLATE.format(chunk_text=chunk_text),
                }
            ],
        )

    def _refine(self, current: List[Participant], chunk_text: str) -> List[Participant]:
        # Use REFINE_PROMPT_TEMPLATE
        return self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=List[Participant],
            messages=[
                {
                    "role": "user",
                    "content": REFINE_PROMPT_TEMPLATE.format(
                        current_json=current, chunk_text=chunk_text
                    ),
                }
            ],
        )

    def _chunk_text(self, text: str) -> list[Chunk]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_config.CHUNK_SIZE,
            chunk_overlap=self.chunk_config.CHUNK_OVERLAP,
        )

        chunks = text_splitter.split_text(text)
        chunked_documents = [Document(page_content=chunk) for chunk in chunks]

        logger.info("Nb of chunked documents: {}", len(chunked_documents))

        chunks_with_ids = [
            Chunk(id=idx, text=doc.page_content)
            for idx, doc in enumerate(chunked_documents)
        ]

        logger.debug("chunks_with_ids {}", chunks_with_ids)

        return chunks_with_ids
