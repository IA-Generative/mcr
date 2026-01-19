"""
Transcribe audio and apply some postprocessing to filter speech.

This module provide the necessary to transcribe audio using whisper, and remove
whisper segments which can be considered "non speech" according to its speech probability.
"""

from io import BytesIO
from typing import Any, List, Optional

from mcr_meeting.app.schemas.transcription_schema import TranscriptionSegment
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline

speech_to_text_pipeline = SpeechToTextPipeline()


def speech_to_text_transcription(  # type: ignore[explicit-any]
    audio_bytes: BytesIO,
    model: Optional[Any] = None,
) -> List[TranscriptionSegment]:
    """
    Transcribe an uploaded audio file into text using whisper_timestamped framework.

    Args:
        audio_bytes: audio bytes to be transcribed. This is a required parameter.
        model (str, optional): The name of the transcription model to be used. This is an optional parameter.

    Returns:
        List[TranscriptionSegment]: A list of TranscriptionSegment objects containing the transcription results.
    """

    segments_with_speakers = speech_to_text_pipeline.run(audio_bytes, model)
    return segments_with_speakers
