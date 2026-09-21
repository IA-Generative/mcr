"""The AI gateway cuts an idle upstream connection after one hour, and a
non-streamed completion sends nothing until the model finishes. Every call
must therefore stream, so bytes keep flowing and no proxy times out."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.exceptions.exceptions import LLMCompletionError
from mcr_meeting.app.infrastructure.llm.client import _build_llm_client, complete

GATEWAY_TIMEOUT_SECONDS = 3600.0


class _Person(BaseModel):
    name: str


def _stream_of(*payloads: str) -> Iterator[Any]:
    for payload in payloads:
        for char in payload:
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=char))],
                usage=None,
            )
    yield SimpleNamespace(choices=[], usage=SimpleNamespace(total_tokens=7))


@pytest.fixture
def llm_client() -> Iterator[MagicMock]:
    client = MagicMock()
    with patch(
        "mcr_meeting.app.infrastructure.llm.client._get_llm_client",
        return_value=client,
    ):
        yield client


def test_configured_timeout_matches_the_gateway_ceiling() -> None:
    assert LLMSettings().LLM_API_TIMEOUT == GATEWAY_TIMEOUT_SECONDS


def test_llm_client_waits_the_full_gateway_hour() -> None:
    with patch(
        "mcr_meeting.app.infrastructure.llm.client.OpenAI", MagicMock()
    ) as openai_cls:
        _build_llm_client()

    assert openai_cls.call_args.kwargs["timeout"] == GATEWAY_TIMEOUT_SECONDS


def test_completion_is_streamed_and_reports_its_usage(llm_client: MagicMock) -> None:
    llm_client.chat.completions.create.return_value = _stream_of('{"name": "Ada"}')

    complete(response_model=_Person, messages=[{"role": "user", "content": "who?"}])

    kwargs = llm_client.chat.completions.create.call_args.kwargs
    assert kwargs["stream"] is True
    assert kwargs["stream_options"] == {"include_usage": True}


def test_returns_the_model_parsed_from_the_concatenated_deltas(
    llm_client: MagicMock,
) -> None:
    llm_client.chat.completions.create.return_value = _stream_of('{"name": "Ada"}')

    result = complete(
        response_model=_Person, messages=[{"role": "user", "content": "who?"}]
    )

    assert result == _Person(name="Ada")


def test_returns_a_bare_list_response_model(llm_client: MagicMock) -> None:
    llm_client.chat.completions.create.return_value = _stream_of(
        '{"content": [{"name": "Ada"}, {"name": "Grace"}]}'
    )

    result = complete(
        response_model=list[_Person], messages=[{"role": "user", "content": "who?"}]
    )

    assert result == [_Person(name="Ada"), _Person(name="Grace")]


def test_reasks_the_model_when_the_streamed_json_is_invalid(
    llm_client: MagicMock,
) -> None:
    llm_client.chat.completions.create.side_effect = [
        _stream_of('{"nome": "Ada"}'),
        _stream_of('{"name": "Ada"}'),
    ]

    result = complete(
        response_model=_Person, messages=[{"role": "user", "content": "who?"}]
    )

    assert result == _Person(name="Ada")
    reask = llm_client.chat.completions.create.call_args.kwargs["messages"]
    assert reask[-2] == {"role": "assistant", "content": '{"nome": "Ada"}'}
    assert "fix the errors" in reask[-1]["content"]


def test_raises_when_every_attempt_streams_invalid_json(llm_client: MagicMock) -> None:
    attempts = LLMSettings().LLM_MAX_RETRIES
    llm_client.chat.completions.create.side_effect = [
        _stream_of("{}") for _ in range(attempts)
    ]

    with pytest.raises(LLMCompletionError):
        complete(response_model=_Person, messages=[{"role": "user", "content": "who?"}])

    assert llm_client.chat.completions.create.call_count == attempts
