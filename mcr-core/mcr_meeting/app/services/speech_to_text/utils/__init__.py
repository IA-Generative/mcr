"""Public exports for the speech_to_text utils package."""

from .audio import split_audio_on_timestamps
from .models import (
    get_diarization_pipeline,
    get_transcription_model,
)
from .vad import (
    convert_to_french_speaker,
    diarize_vad_transcription_segments,
    get_vad_segments_from_diarization,
)

__all__ = [
    "split_audio_on_timestamps",
    "get_transcription_model",
    "get_diarization_pipeline",
    "convert_to_french_speaker",
    "diarize_vad_transcription_segments",
    "get_vad_segments_from_diarization",
]
