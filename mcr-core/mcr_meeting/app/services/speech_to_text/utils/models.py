"""Utility functions for managing speech-to-text models."""

from typing import Optional

from faster_whisper import WhisperModel  # type: ignore[import]
from loguru import logger
from pyannote.audio import Pipeline  # type: ignore[import]

from mcr_meeting.app.configs.base import (
    PyannoteDiarizationParameters,
    Speech2TextSettings,
)
from mcr_meeting.app.utils.compute_devices import (
    get_default_gpu_device,
    is_gpu_available,
)

s2t_settings = Speech2TextSettings()
diarization_settings = PyannoteDiarizationParameters()


min_duration_off = diarization_settings.min_duration_off
threshold = diarization_settings.threshold
min_cluster_size = diarization_settings.min_cluster_size


def set_model(model: Optional[WhisperModel]) -> WhisperModel:
    if model is None:
        try:
            logger.debug("loading model from celery context")
            from mcr_meeting.transcription_worker import context

            model = context.get("model") if context else None
        except ImportError:
            logger.error("no model loaded from celery context")
            model = None
    if model is None:
        raise ValueError("No model specified for transcription.")
    return model


def set_diarization_pipeline() -> Pipeline:
    diarization_pipeline = Pipeline.from_pretrained(
        s2t_settings.DIARIZATION_MODEL,
        use_auth_token=s2t_settings.HUGGINGFACE_API_KEY,
    )

    if is_gpu_available():
        logger.info("Using GPU for diarization")
        diarization_pipeline.to(get_default_gpu_device())

    diarization_pipeline.segmentation.min_duration_off = min_duration_off
    diarization_pipeline.clustering.min_cluster_size = min_cluster_size
    diarization_pipeline.clustering.threshold = threshold
    default_hyperparameters = diarization_pipeline.parameters(instantiated=True)
    logger.info("Default Hyperparameters {}", default_hyperparameters)

    return diarization_pipeline
