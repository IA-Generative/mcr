from collections.abc import Callable
from io import BytesIO

import pytest

from mcr_meeting.app.exceptions.exceptions import SilentAudioError
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    check_audio_is_not_silent,
    compute_silence_ratio,
)


class TestComputeSilenceRatio:
    def test_silent_audio_has_ratio_near_one(
        self, create_silent_audio_buffer: Callable[[float], BytesIO]
    ):
        wav = create_silent_audio_buffer(5.0)
        ratio = compute_silence_ratio(wav)
        assert ratio >= 0.95

    def test_non_silent_audio_has_low_ratio(
        self, create_audio_buffer: Callable[[str], BytesIO]
    ):
        wav = create_audio_buffer("wav")
        ratio = compute_silence_ratio(wav)
        assert ratio < 0.5

    def test_empty_audio_returns_one(self):
        wav = BytesIO(b"\x00" * 44)  # Header only, no PCM data
        assert compute_silence_ratio(wav) == 1.0


class TestCheckAudioIsNotSilent:
    def test_raises_on_silent_audio(
        self, create_silent_audio_buffer: Callable[[float], BytesIO]
    ):
        wav = create_silent_audio_buffer(5.0)
        with pytest.raises(SilentAudioError, match="Silent audio detected"):
            check_audio_is_not_silent(wav)

    def test_passes_on_non_silent_audio(
        self, create_audio_buffer: Callable[[str], BytesIO]
    ):
        wav = create_audio_buffer("wav")
        check_audio_is_not_silent(wav)  # Should not raise
