"""Utility functions for processing audio and transcription segments during Speech To Text pipeline."""

from collections.abc import Iterator
from io import BytesIO

import numpy as np
import soundfile as sf
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan


class TranscriptionInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio: NDArray[np.float32]
    span: TimeSpan


def split_audio_on_timestamps(
    audio_bytes: BytesIO,
    result_with_time: list[TimeSpan],
) -> Iterator[TranscriptionInput]:
    """
    Split mono audio bytes into chunks based on time spans.

    Args:
        audio_bytes (bytes): Full audio data (mono WAV/PCM encoded).
        result_with_time (List[TimeSpan]): Spans with start/end times in seconds.

    Returns:
        Iterator[TranscriptionInput]: List of audio chunks aligned with time spans.
    """
    with sf.SoundFile(audio_bytes) as f:
        sample_rate = f.samplerate
        total_frames = len(f)
        for span in result_with_time:
            start_sample = min(int(span.start * sample_rate), total_frames)
            end_sample = min(int(span.end * sample_rate), total_frames)
            f.seek(start_sample)
            chunk_data = f.read(end_sample - start_sample, dtype="float32")
            yield TranscriptionInput(audio=chunk_data, span=span)
