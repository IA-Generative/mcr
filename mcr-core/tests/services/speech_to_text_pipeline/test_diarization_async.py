"""Unit tests for the async diarization path (job submit + adaptive polling)."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import httpx
import pytest

from mcr_meeting.app.configs.base import TranscriptionApiSettings
from mcr_meeting.app.exceptions.exceptions import (
    DiarizationError,
    MCRException,
    UnknownDiarizationStatus,
)
from mcr_meeting.app.services.speech_to_text import diarization_processor as dp
from mcr_meeting.app.services.speech_to_text.diarization_processor import (
    DiarizationProcessor,
    next_poll_interval,
)

FAST = dp.api_settings.DIARIZATION_POLL_FAST_INTERVAL_SECONDS
SLOW = dp.api_settings.DIARIZATION_POLL_SLOW_INTERVAL_SECONDS
Y = dp.api_settings.DIARIZATION_POLL_LONG_AUDIO_THRESHOLD_SECONDS


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

    def test_raises_for_http_error(self) -> None:
        processor = DiarizationProcessor()
        client = self._mock_client({})
        client.post.return_value.raise_for_status.side_effect = RuntimeError("boom")

        with (
            patch.object(processor, "_get_http_client", return_value=client),
            pytest.raises(RuntimeError),
        ):
            processor._submit_diarization_job(BytesIO(b"audio"))


class TestNextPollInterval:
    def test_near_front_is_fast_even_after_threshold(self) -> None:
        assert next_poll_interval(phase_elapsed_s=Y + 100, queue_position=1) == FAST

    def test_short_phase_is_fast(self) -> None:
        assert next_poll_interval(phase_elapsed_s=Y - 1, queue_position=8) == FAST

    def test_long_phase_not_near_front_is_slow(self) -> None:
        assert next_poll_interval(phase_elapsed_s=Y, queue_position=8) == SLOW

    def test_no_queue_position_within_threshold_is_fast(self) -> None:
        assert next_poll_interval(phase_elapsed_s=Y - 1, queue_position=None) == FAST

    def test_no_queue_position_after_threshold_is_slow(self) -> None:
        assert next_poll_interval(phase_elapsed_s=Y + 1, queue_position=None) == SLOW


def _get_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _client_returning(*items: object) -> MagicMock:
    """Mock httpx client whose successive GET calls yield the given items
    (a payload dict -> response, or an exception -> raised)."""
    client = MagicMock()
    client.get.side_effect = [
        item if isinstance(item, BaseException) else _get_response(item)
        for item in items
    ]
    return client


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://gateway/jobs/audio/job-1")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=response
    )


class TestPollDiarizationJob:
    def _poll(self, processor: DiarizationProcessor, client: MagicMock) -> object:
        with (
            patch.object(processor, "_get_http_client", return_value=client),
            patch.object(dp.time, "sleep"),
        ):
            return processor._poll_diarization_job("job-1")

    def test_nominal_pending_processing_completed(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning(
            {"status": "pending", "queue_position": 3},
            {"status": "processing"},
            {
                "status": "completed",
                "result": {
                    "segments": [
                        {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.7},
                        {"speaker": "SPEAKER_01", "start": 7.3, "end": 12.7},
                    ]
                },
            },
        )

        segments = self._poll(processor, client)

        assert [(s.speaker, s.start, s.end) for s in segments] == [
            ("LOCUTEUR_00", 0.0, 2.7),
            ("LOCUTEUR_01", 7.3, 12.7),
        ]

    def test_failed_raises_diarization_error(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning({"status": "failed", "error": "boom"})

        with pytest.raises(DiarizationError, match="boom"):
            self._poll(processor, client)

    def test_unknown_status_is_fail_loud(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning({"status": "queued"})

        with pytest.raises(UnknownDiarizationStatus, match="queued"):
            self._poll(processor, client)

    def test_completed_with_no_segments_raises(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning({"status": "completed", "result": {"segments": []}})

        with pytest.raises(DiarizationError, match="no segments"):
            self._poll(processor, client)

    def test_transient_errors_then_success(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning(
            httpx.ReadTimeout("timeout"),
            httpx.ConnectError("down"),
            {
                "status": "completed",
                "result": {
                    "segments": [{"speaker": "SPEAKER_00", "start": 0, "end": 1}]
                },
            },
        )

        segments = self._poll(processor, client)

        assert [s.speaker for s in segments] == ["LOCUTEUR_00"]

    def test_transient_errors_exceed_threshold(self) -> None:
        processor = DiarizationProcessor()
        budget = dp.api_settings.DIARIZATION_POLL_MAX_TRANSIENT_ERRORS
        client = _client_returning(
            *[httpx.ReadTimeout("timeout") for _ in range(budget + 1)]
        )

        with pytest.raises(DiarizationError, match="transient errors"):
            self._poll(processor, client)

    def test_unauthorized_fails_fast_without_retrying(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning(_status_error(401))

        with pytest.raises(DiarizationError, match="unauthorized"):
            self._poll(processor, client)

        # No retry: a 401 is permanent, so the budget is never burned.
        assert client.get.call_count == 1

    def test_forbidden_fails_fast(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning(_status_error(403))

        with pytest.raises(DiarizationError, match="unauthorized"):
            self._poll(processor, client)

    def test_server_error_is_still_transient(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning(
            _status_error(503),
            {
                "status": "completed",
                "result": {
                    "segments": [{"speaker": "SPEAKER_00", "start": 0, "end": 1}]
                },
            },
        )

        segments = self._poll(processor, client)

        assert [s.speaker for s in segments] == ["LOCUTEUR_00"]

    def test_adaptive_cadence_sequence(self) -> None:
        """pending(qp=8, t>=Y) -> processing(phase reset, t<Y) -> processing(t>=Y)
        -> completed must sleep SLOW, FAST, SLOW (processing reopens a FAST window)."""
        processor = DiarizationProcessor()
        client = _client_returning(
            {"status": "pending", "queue_position": 8},
            {"status": "processing"},
            {"status": "processing"},
            {
                "status": "completed",
                "result": {
                    "segments": [{"speaker": "SPEAKER_00", "start": 0, "end": 1}]
                },
            },
        )
        # monotonic() calls, in order: started_at, then per iteration
        # (deadline check, optional phase reset, phase_elapsed).
        clock = [0, 0, Y, Y, Y, Y + 1, Y + 1, 2 * Y + 5, 2 * Y + 6]

        with (
            patch.object(processor, "_get_http_client", return_value=client),
            patch.object(dp.time, "sleep") as mock_sleep,
            patch.object(dp.time, "monotonic", side_effect=clock),
        ):
            processor._poll_diarization_job("job-1")

        assert [c.args[0] for c in mock_sleep.call_args_list] == [SLOW, FAST, SLOW]

    def test_deadline_exceeded(self) -> None:
        processor = DiarizationProcessor()
        client = _client_returning({"status": "pending"})
        deadline = dp.celery_settings.REDIS_VISIBILITY_TIMEOUT

        with (
            patch.object(processor, "_get_http_client", return_value=client),
            patch.object(dp.time, "sleep"),
            patch.object(dp.time, "monotonic", side_effect=[0.0, deadline + 1]),
        ):
            with pytest.raises(DiarizationError, match="deadline"):
                processor._poll_diarization_job("job-1")


class TestDiarizeRouting:
    def _diarize_with_flag(self, enabled: bool) -> tuple[MagicMock, MagicMock]:
        processor = DiarizationProcessor()
        ff_client = MagicMock()
        ff_client.is_enabled.return_value = enabled

        with (
            patch.object(dp, "get_feature_flag_client", return_value=ff_client),
            patch.object(processor, "_diarize_async_api") as mock_async,
            patch.object(processor, "_diarize_local") as mock_local,
        ):
            processor.diarize(BytesIO(b"audio"))

        return mock_async, mock_local

    def test_routes_to_async_api_when_flag_on(self) -> None:
        mock_async, mock_local = self._diarize_with_flag(enabled=True)

        mock_async.assert_called_once()
        mock_local.assert_not_called()

    def test_routes_to_local_when_flag_off(self) -> None:
        mock_async, mock_local = self._diarize_with_flag(enabled=False)

        mock_local.assert_called_once()
        mock_async.assert_not_called()

    def test_sync_diarize_api_is_removed(self) -> None:
        assert not hasattr(DiarizationProcessor, "_diarize_api")


class TestHttpClientTimeout:
    def test_client_uses_explicit_timeout(self) -> None:
        processor = DiarizationProcessor()

        with patch.object(dp.httpx, "Client") as mock_client_cls:
            processor._get_http_client()

        timeout = mock_client_cls.call_args.kwargs["timeout"]
        assert timeout is not None
        assert timeout == dp.api_settings.DIARIZATION_POLL_HTTP_TIMEOUT_SECONDS

    def test_client_sends_bearer_auth_on_every_request(self) -> None:
        # The Authorization header lives on the client (default header) so both
        # the POST and the polling GET are authenticated — not just the POST.
        processor = DiarizationProcessor()

        with patch.object(dp.httpx, "Client") as mock_client_cls:
            processor._get_http_client()

        headers = mock_client_cls.call_args.kwargs["headers"]
        assert headers["Authorization"] == (
            f"Bearer {dp.api_settings.DIARIZATION_API_KEY}"
        )
