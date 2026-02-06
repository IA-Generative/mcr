"""Utility functions for managing speech-to-text models."""

from faster_whisper import WhisperModel  # type: ignore[import]
from loguru import logger
from pyannote.audio import Pipeline  # type: ignore[import]


def get_transcription_model_from_worker_context() -> WhisperModel:
    """Return the transcription model from the context of the transcription worker.

    Returns:
        WhisperModel: the whisper model used for transcription.
    """
    try:
        logger.debug("loading model from celery context")
        from mcr_meeting.transcription_worker import context

        model = context.get("model")
        return model
    except ImportError:
        logger.error("no model loaded from celery context")
        raise ValueError("No model specified for transcription.")


def get_diarization_pipeline_from_worker_context() -> Pipeline:
    """Return the diarization pipeline from the context of the transcription worker.

    Returns:
        Pipeline: the pyannote pipeline used for diarization.
    """
    try:
        logger.debug("loading diarization pipeline from celery context")
        from mcr_meeting.transcription_worker import context

        diarization_pipeline = context.get("diarization_pipeline")
        return diarization_pipeline
    except ImportError:
        logger.error("no diarization pipeline loaded from celery context")
        raise ValueError("No diarization pipeline specified.")
