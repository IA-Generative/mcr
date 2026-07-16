import json

from mcr_meeting.app.infrastructure.llm.client import complete
from mcr_meeting.app.infrastructure.llm.prompts.participants import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)
from mcr_meeting.app.schemas.transcription_schema import Participant


def extract_participants(chunk_text: str) -> list[Participant]:
    result = complete(
        response_model=list[Participant],
        messages=[
            {
                "role": "user",
                "content": INITIAL_PROMPT_TEMPLATE.format(chunk_text=chunk_text),
            }
        ],
    )
    return result


def refine_participants(
    current: list[Participant], chunk_text: str
) -> list[Participant]:
    current_json = json.dumps(
        [p.model_dump() for p in current], ensure_ascii=False, indent=2
    )
    result: list[Participant] = complete(
        response_model=list[Participant],
        messages=[
            {
                "role": "user",
                "content": REFINE_PROMPT_TEMPLATE.format(
                    current_json=current_json, chunk_text=chunk_text
                ),
            }
        ],
    )
    return result
