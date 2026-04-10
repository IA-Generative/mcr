"""Unit tests for noise detection functions."""

from io import BytesIO
from unittest.mock import patch

import pytest

from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    _parse_loudnorm_stats,
    _parse_mean_volume,
    _parse_silence_intervals,
    is_audio_noisy,
)


class TestParseMeanVolume:
    def test_valid_output(self):
        stderr = "[Parsed_volumedetect_0 @ 0x...] mean_volume: -20.5 dB\n"
        assert _parse_mean_volume(stderr) == -20.5

    def test_negative_integer(self):
        stderr = "mean_volume: -30 dB\n"
        assert _parse_mean_volume(stderr) == -30.0

    def test_invalid_output_raises(self):
        with pytest.raises(RuntimeError, match="Could not parse mean_volume"):
            _parse_mean_volume("no volume info here")


class TestParseSilenceIntervals:
    def test_valid_output(self):
        stderr = (
            "[silencedetect @ 0x...] silence_start: 1.5\n"
            "[silencedetect @ 0x...] silence_end: 3.2 | silence_duration: 1.7\n"
            "[silencedetect @ 0x...] silence_start: 5.0\n"
            "[silencedetect @ 0x...] silence_end: 7.8 | silence_duration: 2.8\n"
        )
        result = _parse_silence_intervals(stderr)
        assert result == [(1.5, 3.2), (5.0, 7.8)]

    def test_no_silence(self):
        assert _parse_silence_intervals("no silence detected") == []


class TestParseLoudnormStats:
    def test_valid_output(self):
        stderr = (
            "[Parsed_loudnorm_0 @ 0x...] \n"
            "{\n"
            '    "input_i" : "-25.03",\n'
            '    "input_tp" : "-3.05",\n'
            '    "input_lra" : "8.30",\n'
            '    "input_thresh" : "-35.50",\n'
            '    "target_offset" : "2.03"\n'
            "}\n"
        )
        stats = _parse_loudnorm_stats(stderr)
        assert stats["input_i"] == "-25.03"
        assert stats["target_offset"] == "2.03"

    def test_invalid_output_raises(self):
        with pytest.raises(RuntimeError, match="Could not parse loudnorm stats"):
            _parse_loudnorm_stats("no json here")


class TestIsAudioNoisy:
    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.compute_spectral_flatness_on_silences"
    )
    def test_clean_audio(self, mock_flatness):
        mock_flatness.return_value = 0.01
        wav_bytes = BytesIO(b"fake wav data")
        assert is_audio_noisy(wav_bytes) is False
        assert wav_bytes.tell() == 0  # cursor reset

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.compute_spectral_flatness_on_silences"
    )
    def test_noisy_audio(self, mock_flatness):
        mock_flatness.return_value = 0.1
        wav_bytes = BytesIO(b"fake wav data")
        assert is_audio_noisy(wav_bytes) is True
        assert wav_bytes.tell() == 0

    @patch(
        "mcr_meeting.app.services.audio_pre_transcription_processing_service.compute_spectral_flatness_on_silences"
    )
    def test_no_silence_segments(self, mock_flatness):
        mock_flatness.return_value = None
        wav_bytes = BytesIO(b"fake wav data")
        assert is_audio_noisy(wav_bytes) is True
