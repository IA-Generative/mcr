"""Tests for rejecting transcodes whose duration drifts from the input's."""

from io import BytesIO

import pytest

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.domain.audio import check_transcode_preserved_duration
from mcr_meeting.app.exceptions.exceptions import AudioSignalLossError

_settings = AudioSettings()

_INPUT_SECONDS = 10.0
_OUTPUT_WITHIN_TOLERANCE_SECONDS = 9.9
_OUTPUT_LOST_AUDIO_SECONDS = 9.7
_OUTPUT_GAINED_AUDIO_SECONDS = 10.3


def _wav_of(seconds: float) -> BytesIO:
    bytes_per_second = (
        _settings.SAMPLE_RATE * _settings.NB_AUDIO_CHANNELS * _settings.BYTES_PER_SAMPLE
    )
    return BytesIO(
        b"\0" * (_settings.WAV_HEADER_SIZE + int(seconds * bytes_per_second))
    )


def test_transcode_within_tolerance_is_accepted():
    check_transcode_preserved_duration(
        _INPUT_SECONDS, _wav_of(_OUTPUT_WITHIN_TOLERANCE_SECONDS)
    )


def test_transcode_that_lost_audio_is_rejected_with_both_durations():
    with pytest.raises(
        AudioSignalLossError,
        match=f"input={_INPUT_SECONDS:.2f}s output={_OUTPUT_LOST_AUDIO_SECONDS:.2f}s",
    ):
        check_transcode_preserved_duration(
            _INPUT_SECONDS, _wav_of(_OUTPUT_LOST_AUDIO_SECONDS)
        )


def test_transcode_that_gained_audio_is_rejected():
    with pytest.raises(AudioSignalLossError):
        check_transcode_preserved_duration(
            _INPUT_SECONDS, _wav_of(_OUTPUT_GAINED_AUDIO_SECONDS)
        )


def test_recording_without_declared_duration_is_never_rejected():
    check_transcode_preserved_duration(None, _wav_of(_INPUT_SECONDS))
