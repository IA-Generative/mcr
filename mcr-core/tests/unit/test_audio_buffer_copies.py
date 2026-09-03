import tracemalloc
from collections.abc import Callable
from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from mcr_meeting.app.domain.audio import (
    _detect_silences,
    _detect_silences_absolute,
    _get_audio_duration_seconds,
    _get_mean_volume_db,
    _read_audio_samples,
    audio_bytes_to_wav_bytes,
    compute_silence_ratio,
    filter_noise_from_audio_bytes,
    two_pass_volume_normalization,
)

SAMPLE_RATE = 16000
DURATION_SECONDS = 30.0


@pytest.fixture
def recording() -> BytesIO:
    rng = np.random.default_rng(0)
    samples = (
        rng.integers(-32768, 32768, int(DURATION_SECONDS * SAMPLE_RATE), dtype=np.int16)
        // 4
    )
    wav = BytesIO()
    sf.write(wav, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    wav.seek(0)
    return wav


def _peak_allocation(work: Callable[[], object]) -> int:
    tracemalloc.start()
    try:
        work()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak


@pytest.mark.parametrize(
    "step",
    [
        _detect_silences,
        _detect_silences_absolute,
        _get_audio_duration_seconds,
        _get_mean_volume_db,
        compute_silence_ratio,
    ],
)
def test_analysis_steps_do_not_copy_the_recording(
    step: Callable[[BytesIO], object], recording: BytesIO
) -> None:
    size = len(recording.getbuffer())

    peak = _peak_allocation(lambda: step(recording))

    assert peak < size * 0.5


def test_transcoding_holds_one_copy_of_its_output(recording: BytesIO) -> None:
    size = len(recording.getbuffer())

    peak = _peak_allocation(lambda: audio_bytes_to_wav_bytes(recording))

    assert peak < size * 1.5


@pytest.mark.parametrize("step", [filter_noise_from_audio_bytes, _read_audio_samples])
def test_filter_steps_hold_only_their_output(
    step: Callable[[BytesIO], object], recording: BytesIO
) -> None:
    size = len(recording.getbuffer())

    peak = _peak_allocation(lambda: step(recording))

    assert peak < size * 2.5


def test_two_pass_normalization_holds_only_its_output(recording: BytesIO) -> None:
    size = len(recording.getbuffer())

    peak = _peak_allocation(lambda: two_pass_volume_normalization(recording))

    assert peak < size * 1.5
