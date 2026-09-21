"""The AI gateway cuts an idle upstream connection after one hour.
mcr-core must wait that long before it gives up, otherwise it closes the
socket first and the gateway logs a 499."""

from unittest.mock import MagicMock, patch

from mcr_meeting.app.configs.base import LLMSettings
from mcr_meeting.app.infrastructure.llm.client import _build_llm_client

GATEWAY_TIMEOUT_SECONDS = 3600.0


def test_configured_timeout_matches_the_gateway_ceiling() -> None:
    assert LLMSettings().LLM_API_TIMEOUT == GATEWAY_TIMEOUT_SECONDS


def test_llm_client_waits_the_full_gateway_hour() -> None:
    with patch(
        "mcr_meeting.app.infrastructure.llm.client.OpenAI", MagicMock()
    ) as openai_cls:
        _build_llm_client()

    assert openai_cls.call_args.kwargs["timeout"] == GATEWAY_TIMEOUT_SECONDS
