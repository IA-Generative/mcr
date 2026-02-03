"""Utility functions for managing speech-to-text models."""

from faster_whisper import WhisperModel  # type: ignore[import]
from loguru import logger
from pyannote.audio import Pipeline  # type: ignore[import]

from mcr_meeting.app.configs.base import (
    PyannoteDiarizationParameters,
    Speech2TextSettings,
)

s2t_settings = Speech2TextSettings()
diarization_settings = PyannoteDiarizationParameters()


min_duration_off = diarization_settings.min_duration_off
threshold = diarization_settings.threshold
min_cluster_size = diarization_settings.min_cluster_size


def set_model() -> WhisperModel:
    try:
        logger.debug("loading model from celery context")
        from mcr_meeting.transcription_worker import context

        model = context.get("model") if context else None
        return model
    except ImportError:
        logger.error("no model loaded from celery context")
        raise ValueError("No model specified for transcription.")


def set_diarization_pipeline() -> Pipeline:
    try:
        logger.debug("loading diarization pipeline from celery context")
        from mcr_meeting.transcription_worker import context

        diarization_pipeline = context.get("diarization_pipeline") if context else None
        return diarization_pipeline
    except ImportError:
        logger.error("no diarization pipeline loaded from celery context")
        raise ValueError("No diarization pipeline specified.")
