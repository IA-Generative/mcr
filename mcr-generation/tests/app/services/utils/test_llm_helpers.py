"""Unit tests for services.utils.llm_helpers."""

from unittest.mock import MagicMock

import langfuse
import pytest
from pydantic import BaseModel

from mcr_generation.app.exceptions.exceptions import LLMCallError
from mcr_generation.app.services.utils.llm_helpers import (
    _emit_retry_event,
    call_llm_with_structured_output,
)


class _FakeResponse(BaseModel):
    text: str


class TestCallLLMWithStructuredOutput:
    def test_returns_response_on_success(
        self, mock_instructor_client: MagicMock
    ) -> None:
        expected = _FakeResponse(text="hello")
        mock_instructor_client.chat.completions.create.return_value = expected

        result = call_llm_with_structured_output(
            client=mock_instructor_client,
            response_model=_FakeResponse,
            user_message_content="ping",
        )

        assert result == expected

    def test_wraps_client_errors_as_llm_call_error(
        self, mock_instructor_client: MagicMock
    ) -> None:
        mock_instructor_client.chat.completions.create.side_effect = RuntimeError(
            "boom"
        )

        with pytest.raises(LLMCallError, match="LLM call failed for _FakeResponse"):
            call_llm_with_structured_output(
                client=mock_instructor_client,
                response_model=_FakeResponse,
                user_message_content="ping",
            )

    def test_extracts_usage_details_from_raw_response(
        self, mock_instructor_client: MagicMock
    ) -> None:
        langfuse_client = langfuse.get_client.return_value
        langfuse_client.reset_mock()

        response = MagicMock()
        response._raw_response.usage.prompt_tokens = 12
        response._raw_response.usage.completion_tokens = 34
        response._raw_response.usage.total_tokens = 46
        mock_instructor_client.chat.completions.create.return_value = response

        call_llm_with_structured_output(
            client=mock_instructor_client,
            response_model=_FakeResponse,
            user_message_content="ping",
        )

        langfuse_client.update_current_generation.assert_any_call(
            usage_details={"input": 12, "output": 34, "total": 46}
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
