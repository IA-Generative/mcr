"""Utility functions for processing audio and transcription segments during Speech To Text pipeline."""

from io import BytesIO
from typing import List

import soundfile as sf
from loguru import logger

from mcr_meeting.app.services.speech_to_text.types import (
    DiarizationSegment,
    TranscriptionInput,
)
from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan


def split_audio_on_timestamps(
    audio_bytes: BytesIO,
    result_with_time: List[DiarizationSegment],
) -> List[TranscriptionInput]:
    """
    Split mono audio bytes into chunks based on diarization segments.

    Args:
        audio_bytes (bytes): Full audio data (mono WAV/PCM encoded).
        result_with_time (List[DiarizationSegment]): Segments with start/end times in seconds.

    Returns:
        List[TranscriptionInput]: List of audio chunks aligned with diarization segments.
    """
    data, sample_rate = sf.read(audio_bytes)  # already mono
    transcription_inputs: List[TranscriptionInput] = []

    for segment in result_with_time:
        span = TimeSpan(segment.start, segment.end)
        start_sample = int(span.start * sample_rate)
        end_sample = int(span.end * sample_rate)
        chunk_data = data[start_sample:end_sample]

        transcription_inputs.append(
            TranscriptionInput(
                audio=chunk_data.astype("float32"),
                diarization=segment,
            )
        )

    logger.info(
        "Created {} transcription inputs from diarization segments",
        len(transcription_inputs),
    )

    return transcription_inputs
