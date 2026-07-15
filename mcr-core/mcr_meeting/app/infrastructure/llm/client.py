from collections.abc import Iterable

import instructor
from instructor.exceptions import InstructorError
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.exceptions.exceptions import LLMCompletionError


class CorrectedText(BaseModel):
    corrected_text: str


def complete[T: (BaseModel | Iterable[object])](
    response_model: type[T], messages: list[ChatCompletionMessageParam]
) -> T:
    settings = LLMSettings()
    try:
        return _get_llm_client().chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            response_model=response_model,
            temperature=settings.TEMPERATURE,
            max_retries=settings.LLM_MAX_RETRIES,
            messages=messages,
        )
    except InstructorError as e:
        raise LLMCompletionError(str(e)) from e


def _build_llm_client() -> instructor.Instructor:
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


def _get_llm_client() -> instructor.Instructor:
    global _client
    if _client is None:
        _client = _build_llm_client()
    return _client
