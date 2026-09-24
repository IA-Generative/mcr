"""Unit tests for services.utils.llm_helpers."""

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import langfuse
import pytest
from pydantic import BaseModel

from mcr_generation.app.exceptions.exceptions import LLMCallError
from mcr_generation.app.services.utils.llm_helpers import (
    _emit_retry_event,
    async_call_llm_with_structured_output,
    call_llm_with_structured_output,
)


class _FakeResponse(BaseModel):
    text: str


def _chunk(content: str | None, usage: Any = None) -> SimpleNamespace:
    choices = (
        [SimpleNamespace(delta=SimpleNamespace(content=content))]
        if content is not None
        else []
    )
    return SimpleNamespace(choices=choices, usage=usage)


def _stream(payload: str, usage: Any = None) -> Iterator[SimpleNamespace]:
    for char in payload:
        yield _chunk(char)
    yield _chunk(None, usage)


async def _async_stream(payload: str, usage: Any = None) -> Any:
    for chunk in _stream(payload, usage):
        yield chunk


def _usage(prompt: int, completion: int, total: int) -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=prompt, completion_tokens=completion, total_tokens=total
    )


@pytest.fixture
def llm_client() -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = MagicMock()
    return client


class TestCallLLMWithStructuredOutput:
    def test_returns_response_parsed_from_the_stream(
        self, llm_client: MagicMock
    ) -> None:
        llm_client.chat.completions.create.return_value = _stream(
            json.dumps({"text": "hello"})
        )

        result = call_llm_with_structured_output(
            client=llm_client,
            response_model=_FakeResponse,
            user_message_content="ping",
        )

        assert result == _FakeResponse(text="hello")

    def test_asks_the_gateway_to_stream_and_to_report_usage(
        self, llm_client: MagicMock
    ) -> None:
        llm_client.chat.completions.create.return_value = _stream(
            json.dumps({"text": "hello"})
        )

        call_llm_with_structured_output(
            client=llm_client,
            response_model=_FakeResponse,
            user_message_content="ping",
        )

        kwargs = llm_client.chat.completions.create.call_args.kwargs
        assert kwargs["stream"] is True
        assert kwargs["stream_options"] == {"include_usage": True}

    def test_wraps_client_errors_as_llm_call_error(self, llm_client: MagicMock) -> None:
        llm_client.chat.completions.create.side_effect = RuntimeError("boom")

        with pytest.raises(LLMCallError, match="LLM call failed for _FakeResponse"):
            call_llm_with_structured_output(
                client=llm_client,
                response_model=_FakeResponse,
                user_message_content="ping",
                max_retry_attempts=1,
            )

    def test_reasks_the_model_when_the_streamed_json_is_invalid(
        self, llm_client: MagicMock
    ) -> None:
        llm_client.chat.completions.create.side_effect = [
            _stream(json.dumps({"texte": "hello"})),
            _stream(json.dumps({"text": "hello"})),
        ]

        result = call_llm_with_structured_output(
            client=llm_client,
            response_model=_FakeResponse,
            user_message_content="ping",
            retry_min_wait=0,
            retry_max_wait=0,
            retry_wait_multiplier=0,
        )

        assert result == _FakeResponse(text="hello")
        messages = llm_client.chat.completions.create.call_args.kwargs["messages"]
        assert messages[-2]["role"] == "assistant"
        assert "fix the errors" in messages[-1]["content"]

    def test_extracts_usage_details_from_the_final_chunk(
        self, llm_client: MagicMock
    ) -> None:
        langfuse_client = langfuse.get_client.return_value
        langfuse_client.reset_mock()
        llm_client.chat.completions.create.return_value = _stream(
            json.dumps({"text": "hello"}), _usage(12, 34, 46)
        )

        call_llm_with_structured_output(
            client=llm_client,
            response_model=_FakeResponse,
            user_message_content="ping",
        )

        langfuse_client.update_current_generation.assert_any_call(
            usage_details={"input": 12, "output": 34, "total": 46}
        )


class TestAsyncCallLLMWithStructuredOutput:
    @pytest.mark.asyncio
    async def test_returns_response_parsed_from_the_stream(self) -> None:
        client = MagicMock()
        client.chat.completions.create = AsyncMock(
            return_value=_async_stream(json.dumps({"text": "async hello"}))
        )

        result = await async_call_llm_with_structured_output(
            client=client,
            response_model=_FakeResponse,
            user_message_content="ping",
        )

        assert result == _FakeResponse(text="async hello")

    @pytest.mark.asyncio
    async def test_wraps_client_errors_as_llm_call_error(self) -> None:
        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(LLMCallError, match="LLM call failed for _FakeResponse"):
            await async_call_llm_with_structured_output(
                client=client,
                response_model=_FakeResponse,
                user_message_content="ping",
                max_retry_attempts=1,
            )


class TestEmitRetryEvent:
    def test_passes_extracted_state_to_record_llm_retry_event(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_record = MagicMock()
        monkeypatch.setattr(
            "mcr_generation.app.services.utils.llm_helpers.record_llm_retry_event",
            mock_record,
        )

        retry_state = MagicMock()
        retry_state.attempt_number = 3
        retry_state.outcome.exception.return_value = RuntimeError("transient")
        retry_state.next_action.sleep = 1.5

        _emit_retry_event(retry_state)

        mock_record.assert_called_once_with(
            attempt=3,
            next_sleep_seconds=1.5,
            exception_type="RuntimeError",
            exception_msg="transient",
        )
