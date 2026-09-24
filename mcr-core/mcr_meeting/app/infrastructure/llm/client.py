import json
from collections.abc import Iterable, Iterator
from textwrap import dedent
from typing import cast

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError, create_model

from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.exceptions.exceptions import LLMCompletionError


class CorrectedText(BaseModel):
    corrected_text: str


def complete[T: (BaseModel | Iterable[object])](
    response_model: type[T], messages: list[ChatCompletionMessageParam]
) -> T:
    settings = LLMSettings()
    model, is_wrapped = _as_model(response_model)
    conversation: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _json_schema_instruction(model)},
        *messages,
    ]

    last_error: ValidationError | None = None
    for _ in range(settings.LLM_MAX_RETRIES):
        try:
            content = _stream_content(settings, conversation)
        except OpenAIError as error:
            raise LLMCompletionError(str(error)) from error
        try:
            parsed = model.model_validate_json(_json_payload(content))
        except ValidationError as error:
            last_error = error
            conversation.append({"role": "assistant", "content": content})
            conversation.append(
                {
                    "role": "user",
                    "content": f"Recall the function correctly, fix the errors, exceptions found\n{error}",
                }
            )
            continue
        return cast(T, parsed.content if is_wrapped else parsed)  # type: ignore[attr-defined]

    raise LLMCompletionError(str(last_error))


def _as_model(response_model: object) -> tuple[type[BaseModel], bool]:
    if isinstance(response_model, type) and issubclass(response_model, BaseModel):
        return response_model, False
    wrapper = create_model(
        "Response",
        content=(response_model, ...),
        __doc__="Correctly Formatted and Extracted Response.",
    )
    return wrapper, True


def _json_schema_instruction(model: type[BaseModel]) -> str:
    return dedent(
        f"""
        As a genius expert, your task is to understand the content and provide
        the parsed objects in json that match the following json_schema:\n

        {json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False)}

        Make sure to return an instance of the JSON, not the schema itself
        """
    )


def _stream_content(
    settings: LLMSettings, messages: list[ChatCompletionMessageParam]
) -> str:
    stream: Iterator[ChatCompletionChunk] = _get_llm_client().chat.completions.create(
        model=settings.LLM_MODEL_NAME,
        temperature=settings.TEMPERATURE,
        messages=messages,
        response_format={"type": "json_object"},
        stream=True,
        stream_options={"include_usage": True},
    )
    return "".join(
        chunk.choices[0].delta.content
        for chunk in stream
        if chunk.choices and chunk.choices[0].delta.content
    )


def _json_payload(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    fenced = text.split("```")
    if len(fenced) < 2:
        return text
    body = fenced[1]
    if body.startswith("json"):
        body = body[len("json") :]
    return body.strip()


def _build_llm_client() -> OpenAI:
    settings = LLMSettings()
    return OpenAI(
        base_url=settings.LLM_API_BASE_URL,
        api_key=settings.LLM_API_KEY,
        timeout=settings.LLM_API_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )


_client: OpenAI | None = None


def _get_llm_client() -> OpenAI:
    global _client
    if _client is None:
        _client = _build_llm_client()
    return _client
