"""Public exports for the speech_to_text utils package."""

from .audio import split_audio_on_timestamps
from .models import set_diarization_pipeline, set_model
from .vad import (
    convert_to_french_speaker,
    diarize_vad_transcription_segments,
    get_vad_segments_from_diarization,
)

__all__ = [
    "split_audio_on_timestamps",
    "set_model",
    "set_diarization_pipeline",
    "convert_to_french_speaker",
    "diarize_vad_transcription_segments",
    "get_vad_segments_from_diarization",
]
