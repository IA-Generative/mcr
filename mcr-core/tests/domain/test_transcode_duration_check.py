from io import BytesIO

import pytest
from pydub.generators import Sine

from mcr_meeting.app.configs.base import AudioSettings
from mcr_meeting.app.domain.audio import (
    _get_audio_duration_seconds,
    check_transcode_preserved_duration,
    filter_noise_from_audio_bytes,
)
from mcr_meeting.app.exceptions.exceptions import AudioSignalLossError

_settings = AudioSettings()

_INPUT_SECONDS = 10.0
_OUTPUT_WITHIN_TOLERANCE_SECONDS = 9.9
_OUTPUT_LOST_AUDIO_SECONDS = 9.7
_OUTPUT_GAINED_AUDIO_SECONDS = 10.3
_ALTERED_SECONDS = 3


def _wav_of(seconds: float) -> BytesIO:
    bytes_per_second = (
        _settings.SAMPLE_RATE * _settings.NB_AUDIO_CHANNELS * _settings.BYTES_PER_SAMPLE
    )
    return BytesIO(
        b"\0" * (_settings.WAV_HEADER_SIZE + int(seconds * bytes_per_second))
    )


@pytest.fixture
def normalized_recording() -> BytesIO:
    buffer = BytesIO()
    Sine(440).to_audio_segment(duration=_INPUT_SECONDS * 1000).set_frame_rate(
        _settings.SAMPLE_RATE
    ).set_channels(_settings.NB_AUDIO_CHANNELS).set_sample_width(
        _settings.BYTES_PER_SAMPLE
    ).export(buffer, format="wav")
    buffer.seek(0)
    return buffer


def test_transcode_within_tolerance_is_accepted() -> None:
    check_transcode_preserved_duration(
        _INPUT_SECONDS, _wav_of(_OUTPUT_WITHIN_TOLERANCE_SECONDS)
    )


def test_transcode_that_lost_audio_is_rejected_with_both_durations() -> None:
    with pytest.raises(
        AudioSignalLossError,
        match=f"input={_INPUT_SECONDS:.2f}s output={_OUTPUT_LOST_AUDIO_SECONDS:.2f}s",
    ):
        check_transcode_preserved_duration(
            _INPUT_SECONDS, _wav_of(_OUTPUT_LOST_AUDIO_SECONDS)
        )


def test_transcode_that_gained_audio_is_rejected() -> None:
    with pytest.raises(AudioSignalLossError):
        check_transcode_preserved_duration(
            _INPUT_SECONDS, _wav_of(_OUTPUT_GAINED_AUDIO_SECONDS)
        )


def test_recording_without_declared_duration_is_never_rejected() -> None:
    check_transcode_preserved_duration(None, _wav_of(_INPUT_SECONDS))


@pytest.mark.parametrize(
    "filters",
    [
        pytest.param(f"atrim=duration={_ALTERED_SECONDS}", id="lost_audio"),
        pytest.param(f"apad=pad_dur={_ALTERED_SECONDS}", id="gained_audio"),
    ],
)
def test_denoising_that_changes_the_recording_length_is_rejected(
    monkeypatch: pytest.MonkeyPatch, normalized_recording: BytesIO, filters: str
) -> None:
    monkeypatch.setenv("NOISE_FILTERS", filters)

    with pytest.raises(AudioSignalLossError):
        filter_noise_from_audio_bytes(normalized_recording)


def test_default_denoising_keeps_the_recording_length(
    normalized_recording: BytesIO,
) -> None:
    denoised = filter_noise_from_audio_bytes(normalized_recording)

    assert _get_audio_duration_seconds(denoised) == pytest.approx(
        _INPUT_SECONDS, rel=_settings.DURATION_MISMATCH_TOLERANCE
    )
