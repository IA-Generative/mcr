import json
from collections.abc import AsyncIterator, Iterator
from textwrap import dedent
from typing import Any, TypeVar

from langfuse import observe
from loguru import logger
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    Retrying,
    stop_after_attempt,
    wait_exponential,
)

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.exceptions.exceptions import LLMCallError
from mcr_generation.app.utils.langfuse_observability import (
    record_generation_input,
    record_generation_usage,
    record_llm_retry_event,
)

llm_config = LLMConfig()

T = TypeVar("T", bound=BaseModel)


def _emit_retry_event(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    next_sleep = (
        retry_state.next_action.sleep if retry_state.next_action is not None else None
    )
    logger.warning(
        "LLM call retry attempt={}, next_sleep={}s, exception={}: {}",
        retry_state.attempt_number,
        next_sleep,
        type(exc).__name__ if exc else None,
        exc,
    )
    record_llm_retry_event(
        attempt=retry_state.attempt_number,
        next_sleep_seconds=next_sleep,
        exception_type=type(exc).__name__ if exc else None,
        exception_msg=str(exc)[:500] if exc else None,
    )


def _json_schema_instruction(response_model: type[T]) -> str:
    return dedent(
        f"""
        As a genius expert, your task is to understand the content and provide
        the parsed objects in json that match the following json_schema:\n

        {json.dumps(response_model.model_json_schema(), indent=2, ensure_ascii=False)}

        Make sure to return an instance of the JSON, not the schema itself
        """
    )


def _initial_conversation(
    response_model: type[T], user_message_content: str
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _json_schema_instruction(response_model)},
        {"role": "user", "content": user_message_content},
    ]


def _stream_kwargs(
    messages: list[dict[str, str]], model_name: str, temperature: float
) -> dict[str, Any]:
    return {
        "model": model_name,
        "temperature": temperature,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "stream": True,
        "stream_options": {"include_usage": True},
    }


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


def _parse(
    response_model: type[T],
    conversation: list[dict[str, str]],
    content: str,
) -> T:
    try:
        return response_model.model_validate_json(_json_payload(content))
    except ValidationError as error:
        conversation.append({"role": "assistant", "content": content})
        conversation.append(
            {
                "role": "user",
                "content": f"Recall the function correctly, fix the errors, exceptions found\n{error}",
            }
        )
        raise


def _record_usage(usage: Any) -> None:
    if usage is None:
        return
    record_generation_usage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )


def _collect(stream: Iterator[Any]) -> tuple[str, Any]:
    parts: list[str] = []
    usage: Any = None
    for chunk in stream:
        usage = chunk.usage or usage
        if chunk.choices and chunk.choices[0].delta.content:
            parts.append(chunk.choices[0].delta.content)
    return "".join(parts), usage


async def _collect_async(stream: AsyncIterator[Any]) -> tuple[str, Any]:
    parts: list[str] = []
    usage: Any = None
    async for chunk in stream:
        usage = chunk.usage or usage
        if chunk.choices and chunk.choices[0].delta.content:
            parts.append(chunk.choices[0].delta.content)
    return "".join(parts), usage


@observe(as_type="generation", capture_input=False)
def call_llm_with_structured_output(
    client: OpenAI,
    response_model: type[T],
    user_message_content: str,
    model_name: str = llm_config.LLM_MODEL_NAME,
    temperature: float = llm_config.TEMPERATURE,
    max_retry_attempts: int = llm_config.RETRY_MAX_ATTEMPTS,
    retry_wait_multiplier: int = llm_config.RETRY_WAIT_MULTIPLIER,
    retry_min_wait: float = llm_config.RETRY_MIN_WAIT_TIME,
    retry_max_wait: float = llm_config.RETRY_MAX_WAIT_TIME,
) -> T:
    record_generation_input(
        response_model_name=response_model.__name__,
        user_message_content=user_message_content,
        model_name=model_name,
        temperature=temperature,
        max_retry_attempts=max_retry_attempts,
        retry_wait_multiplier=retry_wait_multiplier,
        retry_min_wait=retry_min_wait,
        retry_max_wait=retry_max_wait,
    )
    conversation = _initial_conversation(response_model, user_message_content)

    def _attempt() -> T:
        stream = client.chat.completions.create(
            **_stream_kwargs(conversation, model_name, temperature)
        )
        content, usage = _collect(stream)
        parsed = _parse(response_model, conversation, content)
        _record_usage(usage)
        return parsed

    try:
        return Retrying(
            stop=stop_after_attempt(max_retry_attempts),
            wait=wait_exponential(
                multiplier=retry_wait_multiplier,
                min=retry_min_wait,
                max=retry_max_wait,
            ),
            before_sleep=_emit_retry_event,
            reraise=True,
        )(_attempt)
    except Exception as e:
        raise LLMCallError(f"LLM call failed for {response_model.__name__}: {e}") from e


@observe(as_type="generation", capture_input=False)
async def async_call_llm_with_structured_output(
    client: AsyncOpenAI,
    response_model: type[T],
    user_message_content: str,
    model_name: str = llm_config.LLM_MODEL_NAME,
    temperature: float = llm_config.TEMPERATURE,
    max_retry_attempts: int = llm_config.RETRY_MAX_ATTEMPTS,
    retry_wait_multiplier: int = llm_config.RETRY_WAIT_MULTIPLIER,
    retry_min_wait: float = llm_config.RETRY_MIN_WAIT_TIME,
    retry_max_wait: float = llm_config.RETRY_MAX_WAIT_TIME,
) -> T:
    record_generation_input(
        response_model_name=response_model.__name__,
        user_message_content=user_message_content,
        model_name=model_name,
        temperature=temperature,
        max_retry_attempts=max_retry_attempts,
        retry_wait_multiplier=retry_wait_multiplier,
        retry_min_wait=retry_min_wait,
        retry_max_wait=retry_max_wait,
    )
    conversation = _initial_conversation(response_model, user_message_content)

    async def _attempt() -> T:
        stream = await client.chat.completions.create(
            **_stream_kwargs(conversation, model_name, temperature)
        )
        content, usage = await _collect_async(stream)
        parsed = _parse(response_model, conversation, content)
        _record_usage(usage)
        return parsed

    try:
        return await AsyncRetrying(
            stop=stop_after_attempt(max_retry_attempts),
            wait=wait_exponential(
                multiplier=retry_wait_multiplier,
                min=retry_min_wait,
                max=retry_max_wait,
            ),
            before_sleep=_emit_retry_event,
            reraise=True,
        )(_attempt)
    except Exception as e:
        raise LLMCallError(f"LLM call failed for {response_model.__name__}: {e}") from e
