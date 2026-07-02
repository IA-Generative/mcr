from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.infrastructure.llm.client import CorrectedText, build_llm_client
from mcr_meeting.app.infrastructure.llm.prompts.spelling import PROMPT_TEMPLATE


def correct_spelling(text: str) -> str:
    client = build_llm_client()
    result = client.chat.completions.create(
        model=LLMSettings().LLM_MODEL_NAME,
        response_model=CorrectedText,
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(text=text),
            }
        ],
    )
    return result.corrected_text
