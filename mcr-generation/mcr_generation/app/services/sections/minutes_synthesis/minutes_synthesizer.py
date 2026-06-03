"""Synthétiseur post-reduce : points en suspens et recommandations."""

import json

import instructor
from langfuse import observe
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import MinuteTheme, Participant
from mcr_generation.app.services.sections.minutes_synthesis.prompts import (
    SYNTHESIZE_PROMPT,
)
from mcr_generation.app.services.sections.minutes_synthesis.types import (
    MinutesSynthesisContent,
)
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)


class MinutesSynthesizer:
    """Déduit les points en suspens et recommandations à partir des thèmes consolidés."""

    def __init__(
        self,
        meeting_subject: str | None = None,
        participants: list[Participant] = [],
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

    @observe(name="synthesize_minutes")
    def synthesize(self, themes: list[MinuteTheme]) -> MinutesSynthesisContent:
        if not themes:
            return MinutesSynthesisContent()

        themes_json = json.dumps(
            [theme.model_dump() for theme in themes],
            ensure_ascii=False,
        )

        user_message_content = SYNTHESIZE_PROMPT.format(
            meeting_subject=self.meeting_subject or "Inconnu",
            speaker_mapping=self.speaker_mapping or "Non fourni",
            themes_json=themes_json,
        )

        return call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=MinutesSynthesisContent,
            user_message_content=user_message_content,
        )
