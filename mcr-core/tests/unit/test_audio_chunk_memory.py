import tracemalloc
from io import BytesIO

import numpy as np
import soundfile as sf

from mcr_meeting.app.domain.audio import split_audio_on_timestamps
from mcr_meeting.app.schemas.transcription_schema import TimeSpan

SAMPLE_RATE = 16000


def _pcm16_wav(duration_seconds: float) -> tuple[BytesIO, np.ndarray]:
    rng = np.random.default_rng(0)
    samples = rng.integers(
        -32768, 32768, int(duration_seconds * SAMPLE_RATE), dtype=np.int16
    )
    wav = BytesIO()
    sf.write(wav, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    wav.seek(0)
    return wav, samples


def _spans(duration_seconds: float, chunk_seconds: float) -> list[TimeSpan]:
    starts = np.arange(0, duration_seconds, chunk_seconds)
    return [
        TimeSpan(start=float(s), end=float(min(s + chunk_seconds, duration_seconds)))
        for s in starts
    ]


def test_chunk_samples_are_bit_exact_with_the_source_recording() -> None:
    wav, samples = _pcm16_wav(4.0)

    chunks = split_audio_on_timestamps(wav, _spans(4.0, 1.0))

    restored = np.concatenate([chunk.audio for chunk in chunks])
    assert np.array_equal(restored, samples.astype(np.float32) / 32768.0)
    assert all(chunk.audio.dtype == np.float32 for chunk in chunks)


def test_splitting_allocates_no_more_than_one_float32_copy() -> None:
    duration_seconds = 60.0
    wav, _ = _pcm16_wav(duration_seconds)
    float32_bytes = int(duration_seconds * SAMPLE_RATE) * 4

    tracemalloc.start()
    try:
        chunks = split_audio_on_timestamps(wav, _spans(duration_seconds, 10.0))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert len(chunks) == 6
    assert peak < float32_bytes * 1.5
