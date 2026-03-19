"""Utility functions for processing audio and transcription segments during Speech To Text pipeline."""

from io import BytesIO

import numpy as np
import soundfile as sf
from loguru import logger
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
) -> list[TranscriptionInput]:
    """
    Split mono audio bytes into chunks based on time spans.

    Args:
        audio_bytes (bytes): Full audio data (mono WAV/PCM encoded).
        result_with_time (List[TimeSpan]): Spans with start/end times in seconds.

    Returns:
        List[TranscriptionInput]: List of audio chunks aligned with time spans.
    """
    data, sample_rate = sf.read(audio_bytes)  # already mono
    transcription_inputs: list[TranscriptionInput] = []

    for span in result_with_time:
        start_sample = int(span.start * sample_rate)
        end_sample = int(span.end * sample_rate)
        chunk_data = data[start_sample:end_sample]

        transcription_inputs.append(
            TranscriptionInput(
                audio=chunk_data.astype("float32"),
                span=span,
            )
        )

    logger.debug(
        "Created {} transcription inputs from diarization segments",
        len(transcription_inputs),
    )

    return transcription_inputs
