"""Unit tests for the async diarization path (job submit + adaptive polling)."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.configs.base import TranscriptionApiSettings
from mcr_meeting.app.exceptions.exceptions import (
    MCRException,
    UnknownDiarizationStatus,
)
from mcr_meeting.app.services.speech_to_text import diarization_processor as dp
from mcr_meeting.app.services.speech_to_text.diarization_processor import (
    DiarizationProcessor,
)


class TestPollSettings:
    def test_defaults(self) -> None:
        settings = TranscriptionApiSettings()

        assert settings.DIARIZATION_POLL_FAST_INTERVAL_SECONDS == 10
        assert settings.DIARIZATION_POLL_SLOW_INTERVAL_SECONDS == 90
        assert settings.DIARIZATION_POLL_LONG_AUDIO_THRESHOLD_SECONDS == 180
        assert settings.DIARIZATION_POLL_HTTP_TIMEOUT_SECONDS == 30
        assert settings.DIARIZATION_POLL_MAX_TRANSIENT_ERRORS == 8

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DIARIZATION_POLL_FAST_INTERVAL_SECONDS", "5")
        monkeypatch.setenv("DIARIZATION_POLL_SLOW_INTERVAL_SECONDS", "120")
        monkeypatch.setenv("DIARIZATION_POLL_MAX_TRANSIENT_ERRORS", "3")

        settings = TranscriptionApiSettings()

        assert settings.DIARIZATION_POLL_FAST_INTERVAL_SECONDS == 5
        assert settings.DIARIZATION_POLL_SLOW_INTERVAL_SECONDS == 120
        assert settings.DIARIZATION_POLL_MAX_TRANSIENT_ERRORS == 3


class TestUnknownDiarizationStatus:
    def test_is_mcr_exception(self) -> None:
        assert issubclass(UnknownDiarizationStatus, MCRException)


class TestSubmitDiarizationJob:
    def _mock_client(self, json_payload: dict) -> MagicMock:
        response = MagicMock()
        response.json.return_value = json_payload
        client = MagicMock()
        client.post.return_value = response
        return client

    def test_posts_to_jobs_audio_at_root(self) -> None:
        processor = DiarizationProcessor()
        client = self._mock_client({"job_id": "job-123", "status": "pending"})

        with patch.object(processor, "_get_http_client", return_value=client):
            job_id = processor._submit_diarization_job(BytesIO(b"audio"))

        assert job_id == "job-123"

        url = client.post.call_args.args[0]
        kwargs = client.post.call_args.kwargs
        assert url == f"{dp.api_settings.DIARIZATION_API_BASE_URL}/jobs/audio"
        # DIARIZATION_API_BASE_URL must be the gateway root (no /v1) — the job
        # system is not under the OpenAI-compatible /v1 base.
        assert "/v1/jobs/audio" not in url
        assert "file" in kwargs["files"]
        assert kwargs["data"]["operation"] == "diarization"
        assert kwargs["data"]["model"] == dp.api_settings.DIARIZATION_API_MODEL
        assert (
            kwargs["data"]["min_duration_off"] == dp.diarization_params.min_duration_off
        )
        assert kwargs["data"]["clustering_threshold"] == dp.diarization_params.threshold
        assert kwargs["headers"]["Authorization"] == (
            f"Bearer {dp.api_settings.DIARIZATION_API_KEY}"
        )

    def test_raises_for_http_error(self) -> None:
        processor = DiarizationProcessor()
        client = self._mock_client({})
        client.post.return_value.raise_for_status.side_effect = RuntimeError("boom")

        with (
            patch.object(processor, "_get_http_client", return_value=client),
            pytest.raises(RuntimeError),
        ):
            processor._submit_diarization_job(BytesIO(b"audio"))


class TestHttpClientTimeout:
    def test_client_uses_explicit_timeout(self) -> None:
        processor = DiarizationProcessor()

        with patch.object(dp.httpx, "Client") as mock_client_cls:
            processor._get_http_client()

        timeout = mock_client_cls.call_args.kwargs["timeout"]
        assert timeout is not None
        assert timeout == dp.api_settings.DIARIZATION_POLL_HTTP_TIMEOUT_SECONDS
