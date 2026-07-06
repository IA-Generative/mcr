import instructor
from openai import OpenAI
from pydantic import BaseModel

from mcr_meeting.app.configs.base import LLMSettings


class CorrectedText(BaseModel):
    corrected_text: str


def build_llm_client() -> instructor.Instructor:
    settings = LLMSettings()
    return instructor.from_openai(
        OpenAI(
            base_url=settings.LLM_HUB_API_URL,
            api_key=settings.LLM_HUB_API_KEY,
            timeout=settings.LLM_API_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
        ),
        mode=instructor.Mode.JSON,
    )


_client: instructor.Instructor | None = None


def get_llm_client() -> instructor.Instructor:
    global _client
    if _client is None:
        _client = build_llm_client()
    return _client
