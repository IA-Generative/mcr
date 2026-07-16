from mcr_meeting.app.infrastructure.llm.client import CorrectedText, complete
from mcr_meeting.app.infrastructure.llm.prompts.spelling import PROMPT_TEMPLATE


def correct_spelling(text: str) -> str:
    result = complete(
        response_model=CorrectedText,
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(text=text),
            }
        ],
    )
    return result.corrected_text
