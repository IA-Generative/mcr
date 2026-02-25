import instructor
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel

from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.correct_spelling_mistakes.prompt import PROMPT_TEMPLATE


class CorrectedText(BaseModel):
    corrected_text: str


class SpellingCorrector:
    def __init__(self) -> None:
        self.settings = LLMSettings()
        self.client = instructor.from_openai(
            OpenAI(
                base_url=self.settings.LLM_HUB_API_URL,
                api_key=self.settings.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    def correct(
        self, segments: list[DiarizedTranscriptionSegment]
    ) -> list[DiarizedTranscriptionSegment]:
        if not segments:
            logger.warning("No segments found to correct")
            return []

        return [
            segment.model_copy(update={"text": self._correct_segment(segment.text)})
            for segment in segments
        ]

    def _correct_segment(self, text: str) -> str:
        result = self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=CorrectedText,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(text=text),
                }
            ],
        )
        return result.corrected_text
