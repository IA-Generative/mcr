import json

from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.infrastructure.llm.client import build_llm_client
from mcr_meeting.app.schemas.transcription_schema import Participant
from mcr_meeting.app.services.speech_to_text.participants_naming.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)


def extract_participants(chunk_text: str) -> list[Participant]:
    client = build_llm_client()
    return client.chat.completions.create(
        model=LLMSettings().LLM_MODEL_NAME,
        response_model=list[Participant],
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": INITIAL_PROMPT_TEMPLATE.format(chunk_text=chunk_text),
            }
        ],
    )


def refine_participants(
    current: list[Participant], chunk_text: str
) -> list[Participant]:
    client = build_llm_client()
    current_json = json.dumps(
        [p.model_dump() for p in current], ensure_ascii=False, indent=2
    )
    return client.chat.completions.create(
        model=LLMSettings().LLM_MODEL_NAME,
        response_model=list[Participant],
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": REFINE_PROMPT_TEMPLATE.format(
                    current_json=current_json, chunk_text=chunk_text
                ),
            }
        ],
    )
