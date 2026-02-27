import json

import instructor
from langfuse import observe
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import DetailedDiscussion
from mcr_generation.app.services.sections.discussions_synthesis.prompts import (
    SYNTHETISE_PROMPT,
)
from mcr_generation.app.services.sections.discussions_synthesis.types import Content
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)


@observe(name="synthetise_detailed_discussions")
def synthetise_detailed_discussions(
    detailed_discussions: list[DetailedDiscussion],
    meeting_subject: str | None,
    speaker_mapping: str | None,
) -> Content:
    if not detailed_discussions:
        return Content()

    llm_config = LLMConfig()
    client_instructor = instructor.from_openai(
        OpenAI(
            base_url=llm_config.LLM_HUB_API_URL,
            api_key=llm_config.LLM_HUB_API_KEY,
        ),
        mode=instructor.Mode.JSON,
    )

    detailed_discussions_json = json.dumps(
        [discussion.model_dump() for discussion in detailed_discussions],
        indent=2,
        ensure_ascii=False,
    )

    user_message_content = SYNTHETISE_PROMPT.format(
        meeting_subject=meeting_subject or "Inconnu",
        speaker_mapping=speaker_mapping or "Non fourni",
        detailed_discussions_json=detailed_discussions_json,
    )

    return call_llm_with_structured_output(
        client=client_instructor,
        response_model=Content,
        user_message_content=user_message_content,
    )
