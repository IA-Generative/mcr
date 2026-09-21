import json

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
    def __init__(
        self,
        meeting_subject: str | None = None,
        participants: list[Participant] = [],
    ) -> None:
        self.llm_config = LLMConfig()
        self.llm_client = OpenAI(
            base_url=self.llm_config.LLM_API_BASE_URL,
            api_key=self.llm_config.LLM_API_KEY,
            timeout=self.llm_config.LLM_API_TIMEOUT,
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
            client=self.llm_client,
            response_model=MinutesSynthesisContent,
            user_message_content=user_message_content,
        )
