"""Utility functions for managing speech-to-text models."""

from faster_whisper import WhisperModel  # type: ignore[import]
from loguru import logger
from pyannote.audio import Pipeline  # type: ignore[import]


def get_transcription_model() -> WhisperModel:
    """Return the transcription model.

    Returns:
        WhisperModel: the whisper model used for transcription.
    """
    try:
        logger.debug("loading model from celery context")
        from mcr_meeting.transcription_worker import context

        transcription_model = context.get("model")
        if transcription_model is None:
            logger.error("Transcription model is None in celery context")
            raise ValueError("Transcription model is None in context.")
        return transcription_model
    except ImportError:
        logger.error("no transcription model loaded from celery context")
        raise
    except Exception:
        raise


def get_diarization_pipeline() -> Pipeline:
    """Return the diarization pipeline.

    Returns:
        Pipeline: the pyannote pipeline used for diarization.
    """
    try:
        logger.debug("loading diarization pipeline from celery context")
        from mcr_meeting.transcription_worker import context

        diarization_pipeline = context.get("diarization_pipeline")
        if diarization_pipeline is None:
            logger.error("Diarization pipeline is None in celery context")
            raise ValueError("Diarization pipeline is None in context.")
        return diarization_pipeline
    except ImportError:
        logger.error("no diarization pipeline loaded from celery context")
        raise
    except Exception:
        raise
