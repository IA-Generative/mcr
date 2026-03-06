import re

from loguru import logger
from pydantic import BaseModel

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_spelling_mistakes.prompt import PROMPT_TEMPLATE
from mcr_meeting.app.services.llm_post_processing import Chunk, LLMPostProcessing


class CorrectedText(BaseModel):
    corrected_text: str


class SpellingCorrector(LLMPostProcessing):
    def __init__(self) -> None:
        super().__init__()
        # Removed > on purpose so we can add its index for better splitting later
        self.separator = "<separator"

    def correct(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> list[DiarizedTranscriptionSegment]:
        """
        Corrects spelling mistakes in the given segments using an LLM.

        Args:
            segments (list[DiarizedTranscriptionSegment]): List of diarized transcription segments.

        Returns:
            list[DiarizedTranscriptionSegment]: List of segments with corrected text.
        """
        if not segments:
            logger.warning("No segments found to correct")
            return []

        text = self._format_segments_for_llm(segments)
        chunks = self._chunk_text(text)

        for chunk in chunks:
            chunk.text = self._correct_chunk(chunk)

        texts = self._split_segments(chunks)

        if len(texts) != len(segments):
            logger.warning(
                "Didn't find the same amount of segments after correction. Skipping."
            )
            return segments
        return [
            segment.model_copy(update={"text": text})
            for segment, text in zip(segments, texts)
        ]

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
        return (
            "".join(
                segment.text.strip() + f" {self.separator}{i}>"
                for i, segment in enumerate(segments[:-1])
            )
            + segments[-1].text.strip()
        )

    def _correct_chunk(self, chunk: Chunk) -> str:
        result = self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=CorrectedText,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(text=chunk.text),
                }
            ],
        )
        return result.corrected_text

    def _split_segments(self, chunks: list[Chunk]) -> list[str]:
        text = " ".join(chunk.text for chunk in chunks)
        return re.split(r"<separator\d+>", text)
