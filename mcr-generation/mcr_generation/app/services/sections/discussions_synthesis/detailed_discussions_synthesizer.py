import json

import instructor
from langfuse import observe
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import DetailedDiscussion, Participant
from mcr_generation.app.services.sections.discussions_synthesis.prompts import (
    SYNTHESIZE_PROMPT,
)
from mcr_generation.app.services.sections.discussions_synthesis.types import Content
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)


class DetailedDiscussionsSynthesizer:
    """Synthesizes detailed discussions into a concise summary, to-do list, and to-monitor list."""

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

    @observe(name="synthesize_detailed_discussions")
    def synthesize(
        self,
        detailed_discussions: list[DetailedDiscussion],
    ) -> Content:
        if not detailed_discussions:
            return Content()

        detailed_discussions_json = json.dumps(
            [discussion.model_dump() for discussion in detailed_discussions],
            indent=2,
            ensure_ascii=False,
        )

        user_message_content = SYNTHESIZE_PROMPT.format(
            meeting_subject=self.meeting_subject or "Inconnu",
            speaker_mapping=self.speaker_mapping or "Non fourni",
            detailed_discussions_json=detailed_discussions_json,
        )

        return call_llm_with_structured_output(
            client=self.client_instructor,
            response_model=Content,
            user_message_content=user_message_content,
        )
