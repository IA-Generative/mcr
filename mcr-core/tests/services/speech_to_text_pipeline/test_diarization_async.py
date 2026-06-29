"""Unit tests for the async diarization path (job submit + adaptive polling)."""

import pytest

from mcr_meeting.app.configs.base import TranscriptionApiSettings
from mcr_meeting.app.exceptions.exceptions import (
    MCRException,
    UnknownDiarizationStatus,
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
