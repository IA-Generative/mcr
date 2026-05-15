from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

LLMResponseValues = BaseModel | list[BaseModel] | tuple[BaseModel, ...]


@pytest.fixture
def mock_instructor_client() -> MagicMock:
    """Pre-wired Instructor client — chat.completions.create is a MagicMock."""
    client = MagicMock()
    client.chat.completions.create = MagicMock()
    return client


def _patch_kwargs(values: LLMResponseValues) -> dict[str, Any]:
    """Build the `patch()` kwargs that configure the mock to return `values`:
    a list/tuple is consumed call-by-call via `side_effect`, a single instance
    is returned every call via `return_value`."""
    if isinstance(values, list | tuple):
        return {"side_effect": list(values)}
    return {"return_value": values}


@pytest.fixture
def fake_call_llm_with_structured_output() -> Callable[[str, LLMResponseValues], Any]:
    """Factory fixture: patches the sync `call_llm_with_structured_output` at a
    consumer's import site and returns either the single given value (for every
    call) or each value of a list/tuple in order.

    Usage:
        with fake_call_llm_with_structured_output(module_path, some_value):
            ...
        with fake_call_llm_with_structured_output(module_path, [v1, v2, v3]):
            ...
    """

    @contextmanager
    def _factory(module_path: str, values: LLMResponseValues) -> Iterator[MagicMock]:
        with patch(
            f"{module_path}.call_llm_with_structured_output",
            **_patch_kwargs(values),
        ) as mock:
            yield mock

    return _factory


@pytest.fixture
def fake_async_call_llm_with_structured_output() -> Callable[
    [str, LLMResponseValues], Any
]:
    """Factory fixture: patches the async `async_call_llm_with_structured_output`
    at a consumer's import site and returns either the single given value (for
    every call) or each value of a list/tuple in order.

    Usage:
        with fake_async_call_llm_with_structured_output(module_path, some_value):
            ...
        with fake_async_call_llm_with_structured_output(module_path, [v1, v2, v3]):
            ...
    """

    @contextmanager
    def _factory(module_path: str, values: LLMResponseValues) -> Iterator[AsyncMock]:
        with patch(
            f"{module_path}.async_call_llm_with_structured_output",
            new_callable=AsyncMock,
            **_patch_kwargs(values),
        ) as mock:
            yield mock

    return _factory
