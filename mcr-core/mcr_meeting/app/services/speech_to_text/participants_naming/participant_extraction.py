from loguru import logger
from pydantic import BaseModel, Field

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.llm_post_processing import Chunk, LLMPostProcessing
from mcr_meeting.app.services.speech_to_text.participants_naming.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)


class Participant(BaseModel):
    speaker_id: str = Field(
        description="Identifiant unique du locuteur dans la transcription ex: LOCUTEUR_03.",
    )
    name: str | None = Field(
        None,
        description="Prenom et/ou nom déduit pour le locuteur à partir des interactions dans la transcription. Ex: 'Jean' ou 'Jean Dupont'.",
    )
    role: str | None = Field(
        None,
        description="Fonction/rôle si mentionné ou déduit (ex. PO, Tech Lead, Directeur financier).",
    )
    confidence: float | None = Field(
        ge=0.0,
        le=1.0,
        description="Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain du nom associé locuteur.",
    )
    association_justification: str | None = Field(
        description=(
            "Identification explicite ou déduction par contexte ayant permis d'associer ce nom/rôle au locuteur avec l'id."
        ),
    )


class ParticipantExtraction(LLMPostProcessing):
    def __init__(self) -> None:
        super().__init__()

    def extract(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> list[Participant]:
        text = self._format_segments_for_llm(segments)
        chunks = self._chunk_text(text, chunk_overlap=self.chunk_config.CHUNK_OVERLAP)

        if not chunks:
            logger.warning("No chunks found")
            return []

        # Seed with first chunk
        participants = self._initial_extract(chunks[0])

        # Refine with subsequent chunks
        if len(chunks) > 1:
            for chunk in chunks[1:]:
                participants = self._refine(participants, chunk)

        return participants

    def _format_segments_for_llm(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> str:
        """
        Helper to convert segments into a dialogue string.

        Args:
            segments (list[DiarizedTranscriptionSegment]): List of speaker transcriptions.

        Returns:
            str: Dialogue string.
        """
        return "\n".join([str(seg) for seg in segments])

    def _initial_extract(self, chunk: Chunk) -> list[Participant]:
        # Use INITIAL_PROMPT_TEMPLATE
        return self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=list[Participant],
            messages=[
                {
                    "role": "user",
                    "content": INITIAL_PROMPT_TEMPLATE.format(chunk_text=chunk.text),
                }
            ],
        )

    def _refine(self, current: list[Participant], chunk: Chunk) -> list[Participant]:
        # Use REFINE_PROMPT_TEMPLATE
        return self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=list[Participant],
            messages=[
                {
                    "role": "user",
                    "content": REFINE_PROMPT_TEMPLATE.format(
                        current_json=current, chunk_text=chunk.text
                    ),
                }
            ],
        )
