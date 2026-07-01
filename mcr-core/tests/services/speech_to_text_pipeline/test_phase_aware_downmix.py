"""Tests for the phase-aware mono downmix in audio_bytes_to_wav_bytes."""

import tempfile
from collections.abc import Callable
from io import BytesIO

import pytest

from mcr_meeting.app.domain.audio import (
    _is_phase_inverted_stereo,
    audio_bytes_to_wav_bytes,
    check_audio_is_not_silent,
    compute_silence_ratio,
)
from mcr_meeting.app.exceptions.exceptions import SilentAudioError


def _to_temp_file(buffer: BytesIO) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(buffer.getvalue())
        return tmp.name


class TestIsPhaseInvertedStereo:
    def test_true_for_phase_inverted_stereo(
        self, create_phase_inverted_stereo_buffer: Callable[[float], BytesIO]
    ):
        path = _to_temp_file(create_phase_inverted_stereo_buffer(3.0))
        assert _is_phase_inverted_stereo(path) is True

    def test_false_for_inphase_stereo(
        self, create_inphase_stereo_buffer: Callable[[float], BytesIO]
    ):
        path = _to_temp_file(create_inphase_stereo_buffer(3.0))
        assert _is_phase_inverted_stereo(path) is False

    def test_false_for_mono(self, create_audio_buffer: Callable[[str], BytesIO]):
        path = _to_temp_file(create_audio_buffer("wav"))
        assert _is_phase_inverted_stereo(path) is False


class TestPhaseAwareDownmix:
    def test_phase_inverted_stereo_is_cancelled_without_fix(
        self, create_phase_inverted_stereo_buffer: Callable[[float], BytesIO]
    ):
        """Reproduces the bug: plain averaging downmix silences the speech."""
        wav = audio_bytes_to_wav_bytes(
            create_phase_inverted_stereo_buffer(3.0), phase_aware_downmix=False
        )
        assert compute_silence_ratio(wav) >= 0.95

    def test_phase_inverted_stereo_recovered_with_fix(
        self, create_phase_inverted_stereo_buffer: Callable[[float], BytesIO]
    ):
        """The fix uses the side signal, recovering the speech."""
        wav = audio_bytes_to_wav_bytes(
            create_phase_inverted_stereo_buffer(3.0), phase_aware_downmix=True
        )
        assert compute_silence_ratio(wav) < 0.5
        check_audio_is_not_silent(wav)  # Should not raise

    def test_inphase_stereo_unaffected_by_fix(
        self, create_inphase_stereo_buffer: Callable[[float], BytesIO]
    ):
        """Normal stereo keeps the averaging downmix and stays intelligible."""
        wav = audio_bytes_to_wav_bytes(
            create_inphase_stereo_buffer(3.0), phase_aware_downmix=True
        )
        assert compute_silence_ratio(wav) < 0.5
        check_audio_is_not_silent(wav)  # Should not raise


class TestPhaseInvertedSilentAudioError:
    def test_pre_process_path_raises_without_fix(
        self, create_phase_inverted_stereo_buffer: Callable[[float], BytesIO]
    ):
        wav = audio_bytes_to_wav_bytes(
            create_phase_inverted_stereo_buffer(3.0), phase_aware_downmix=False
        )
        with pytest.raises(SilentAudioError):
            check_audio_is_not_silent(wav)
