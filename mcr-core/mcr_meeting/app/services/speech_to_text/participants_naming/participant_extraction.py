import json

from langfuse import observe
from loguru import logger

from mcr_meeting.app.infrastructure.llm.prompts.participants import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
)
from mcr_meeting.app.services.llm_post_processing import Chunk, LLMPostProcessing
from mcr_meeting.app.utils.langfuse_observability import (
    record_participant_name_lost_event,
)


class ParticipantExtraction(LLMPostProcessing):
    def __init__(self) -> None:
        super().__init__()

    @observe(name="participant_extraction")
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
            for step_index, chunk in enumerate(chunks[1:], start=1):
                previous = participants
                participants = self._refine(participants, chunk)
                self._warn_on_name_loss(
                    previous=previous, current=participants, step_index=step_index
                )

        return participants

    @staticmethod
    def _warn_on_name_loss(
        previous: list[Participant],
        current: list[Participant],
        step_index: int,
    ) -> None:
        previous_by_id = {p.speaker_id: p for p in previous}
        current_by_id = {p.speaker_id: p for p in current}
        for speaker_id, prev in previous_by_id.items():
            if prev.name is None:
                continue
            current_participant = current_by_id.get(speaker_id)
            if current_participant is None:
                logger.warning(
                    "Participant {} (name={!r}) disappeared from the list at step {}",
                    speaker_id,
                    prev.name,
                    step_index,
                )
                record_participant_name_lost_event(
                    speaker_id=speaker_id,
                    step_index=step_index,
                    previous_name=prev.name,
                    reason="disappeared",
                )
            elif current_participant.name is None:
                logger.warning(
                    "Participant {} lost their name at step {} (was {!r})",
                    speaker_id,
                    step_index,
                    prev.name,
                )
                record_participant_name_lost_event(
                    speaker_id=speaker_id,
                    step_index=step_index,
                    previous_name=prev.name,
                    reason="name_set_to_null",
                )

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
        return "\n".join([f"{seg.speaker}: {seg.text}" for seg in segments])

    def _initial_extract(self, chunk: Chunk) -> list[Participant]:
        # Use INITIAL_PROMPT_TEMPLATE
        return self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=list[Participant],
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": INITIAL_PROMPT_TEMPLATE.format(chunk_text=chunk.text),
                }
            ],
        )

    def _refine(self, current: list[Participant], chunk: Chunk) -> list[Participant]:
        # Use REFINE_PROMPT_TEMPLATE
        current_json = json.dumps(
            [p.model_dump() for p in current], ensure_ascii=False, indent=2
        )
        return self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=list[Participant],
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": REFINE_PROMPT_TEMPLATE.format(
                        current_json=current_json, chunk_text=chunk.text
                    ),
                }
            ],
        )
