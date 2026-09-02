import tracemalloc
from io import BytesIO

import numpy as np
import soundfile as sf

from mcr_meeting.app.domain.audio import iter_audio_chunks
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

    chunks = list(iter_audio_chunks(wav, _spans(4.0, 1.0)))

    restored = np.concatenate([chunk.audio for chunk in chunks])
    assert np.array_equal(restored, samples.astype(np.float32) / 32768.0)
    assert all(chunk.audio.dtype == np.float32 for chunk in chunks)


def test_chunks_carry_the_samples_of_their_own_span() -> None:
    wav, samples = _pcm16_wav(4.0)

    chunks = list(iter_audio_chunks(wav, _spans(4.0, 1.0)))

    assert len(chunks) == 4
    for index, chunk in enumerate(chunks):
        expected = samples[index * SAMPLE_RATE : (index + 1) * SAMPLE_RATE]
        assert np.array_equal(chunk.audio, expected.astype(np.float32) / 32768.0)
        assert chunk.span.start == float(index)


def test_a_span_reaching_past_the_recording_yields_what_exists() -> None:
    wav, samples = _pcm16_wav(2.0)
    overshooting = [TimeSpan(start=1.0, end=5.0), TimeSpan(start=3.0, end=4.0)]

    chunks = list(iter_audio_chunks(wav, overshooting))

    assert len(chunks[0].audio) == SAMPLE_RATE
    assert np.array_equal(
        chunks[0].audio, samples[SAMPLE_RATE:].astype(np.float32) / 32768.0
    )
    assert len(chunks[1].audio) == 0


def test_reading_a_chunk_never_decodes_the_whole_recording() -> None:
    duration_seconds = 60.0
    chunk_seconds = 10.0
    wav, _ = _pcm16_wav(duration_seconds)
    chunk_float32_bytes = int(chunk_seconds * SAMPLE_RATE) * 4

    tracemalloc.start()
    try:
        consumed = 0
        for _ in iter_audio_chunks(wav, _spans(duration_seconds, chunk_seconds)):
            consumed += 1
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert consumed == 6
    assert peak < chunk_float32_bytes * 2.5
