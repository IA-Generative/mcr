"""Source-classification of transcription-API faults.

Invariant: a recoverable transcription-API fault (connect blip, timeout, 5xx,
429 overload) must bubble as a TransientInfraError so the Celery task-level
autoretry re-runs the meeting; only a definitive fault (4xx rejection, empty
result, unknown error) fails loud as TranscriptionError. A recoverable fault
wrongly labelled TranscriptionError silently kills a recoverable meeting.
"""

from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import openai
import pytest

from mcr_meeting.app.exceptions.exceptions import (
    TranscriptionError,
    TransientInfraError,
)
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://gateway/v1/audio/transcriptions")
    return httpx.Response(status_code, request=request)


def _status_error(exc_cls: type[openai.APIStatusError], status_code: int) -> Exception:
    return exc_cls("boom", response=_response(status_code), body=None)


def _connection_error() -> Exception:
    request = httpx.Request("POST", "https://gateway/v1/audio/transcriptions")
    return openai.APIConnectionError(request=request)


def _timeout_error() -> Exception:
    request = httpx.Request("POST", "https://gateway/v1/audio/transcriptions")
    return openai.APITimeoutError(request=request)


def _run_chunk_with(exc: Exception) -> None:
    processor = TranscriptionProcessor(MagicMock())
    client = MagicMock()
    client.audio.transcriptions.create.side_effect = exc
    audio = np.zeros(16000, dtype=np.float32)

    with patch.object(processor, "_get_openai_client", return_value=client):
        processor._transcribe_audio_chunk_api(audio)


class TestRecoverableFaultsAreTransient:
    @pytest.mark.parametrize(
        "exc",
        [
            _connection_error(),
            _timeout_error(),
            _status_error(openai.InternalServerError, 500),
            _status_error(openai.APIStatusError, 503),
            _status_error(openai.RateLimitError, 429),
        ],
    )
    def test_recoverable_fault_bubbles_as_transient(self, exc: Exception) -> None:
        with pytest.raises(TransientInfraError):
            _run_chunk_with(exc)


class TestDefinitiveFaultsFailLoud:
    @pytest.mark.parametrize(
        "exc",
        [
            _status_error(openai.BadRequestError, 400),
            _status_error(openai.AuthenticationError, 401),
            _status_error(openai.NotFoundError, 404),
            RuntimeError("something unexpected"),
        ],
    )
    def test_definitive_fault_fails_loud(self, exc: Exception) -> None:
        with pytest.raises(TranscriptionError) as excinfo:
            _run_chunk_with(exc)
        # Must NOT be transient — a definitive fault must not trigger task retries.
        assert not isinstance(excinfo.value, TransientInfraError)

    def test_empty_result_fails_loud(self) -> None:
        processor = TranscriptionProcessor(MagicMock())
        client = MagicMock()
        response = MagicMock()
        response.segments = []
        client.audio.transcriptions.create.return_value = response
        audio = np.zeros(16000, dtype=np.float32)

        with (
            patch.object(processor, "_get_openai_client", return_value=client),
            pytest.raises(TranscriptionError) as excinfo,
        ):
            processor._transcribe_audio_chunk_api(audio)
        assert not isinstance(excinfo.value, TransientInfraError)
