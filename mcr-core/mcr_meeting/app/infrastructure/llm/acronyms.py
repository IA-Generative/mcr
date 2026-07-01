from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.infrastructure.llm.client import CorrectedText, build_llm_client
from mcr_meeting.app.services.correct_acronyms.prompt import (
    ACRONYM_PROMPT_TEMPLATE,
    GLOSSARY_CONTENT,
)

_PROMPT_TEMPLATE = ACRONYM_PROMPT_TEMPLATE.format(
    glossary=GLOSSARY_CONTENT,
    text="{text}",
)


def correct_acronyms(text: str) -> str:
    client = build_llm_client()
    result = client.chat.completions.create(
        model=LLMSettings().LLM_MODEL_NAME,
        response_model=CorrectedText,
        messages=[
            {
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(text=text),
            }
        ],
    )
    return result.corrected_text
