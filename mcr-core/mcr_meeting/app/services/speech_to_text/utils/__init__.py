"""Public exports for the speech_to_text utils package."""

from .audio import split_audio_on_timestamps
from .chunking import compute_transcription_chunks
from .models import (
    get_diarization_pipeline,
    get_transcription_model,
)
from .vad import (
    convert_to_french_speaker,
    diarize_vad_transcription_segments,
)

__all__ = [
    "split_audio_on_timestamps",
    "compute_transcription_chunks",
    "get_transcription_model",
    "get_diarization_pipeline",
    "convert_to_french_speaker",
    "diarize_vad_transcription_segments",
]
