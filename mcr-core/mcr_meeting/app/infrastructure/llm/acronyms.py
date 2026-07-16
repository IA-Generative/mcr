from mcr_meeting.app.infrastructure.llm.client import CorrectedText, complete
from mcr_meeting.app.infrastructure.llm.prompts.acronyms import (
    ACRONYM_PROMPT_TEMPLATE,
    GLOSSARY_CONTENT,
)

_PROMPT_TEMPLATE = ACRONYM_PROMPT_TEMPLATE.format(
    glossary=GLOSSARY_CONTENT,
    text="{text}",
)


def correct_acronyms(text: str) -> str:
    result = complete(
        response_model=CorrectedText,
        messages=[
            {
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(text=text),
            }
        ],
    )
    return result.corrected_text
