import tracemalloc
from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from pytest_mock import MockerFixture

from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import TimeSpan

SAMPLE_RATE = 16000
DURATION_SECONDS = 600.0
CHUNK_SECONDS = 30.0


@pytest.fixture
def long_recording() -> BytesIO:
    rng = np.random.default_rng(0)
    samples = (
        rng.integers(-32768, 32768, int(DURATION_SECONDS * SAMPLE_RATE), dtype=np.int16)
        // 4
    )
    wav = BytesIO()
    sf.write(wav, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    wav.seek(0)
    return wav


def _spans() -> list[TimeSpan]:
    starts = np.arange(0, DURATION_SECONDS, CHUNK_SECONDS)
    return [
        TimeSpan(start=float(s), end=float(min(s + CHUNK_SECONDS, DURATION_SECONDS)))
        for s in starts
    ]


def test_transcription_never_decodes_the_whole_recording(
    mocker: MockerFixture, long_recording: BytesIO
) -> None:
    recording_size = len(long_recording.getbuffer())
    response = SimpleNamespace(
        segments=[SimpleNamespace(start=0.0, end=1.0, text="bonjour")]
    )

    def create(**_: object) -> SimpleNamespace:
        return response

    client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
    )
    mocker.patch.object(
        TranscriptionProcessor, "_get_openai_client", return_value=client
    )

    tracemalloc.start()
    try:
        segments = TranscriptionProcessor().transcribe(long_recording, _spans())
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert len(segments) == 20
    assert peak < recording_size
