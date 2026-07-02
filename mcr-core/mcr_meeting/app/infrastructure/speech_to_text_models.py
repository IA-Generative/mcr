"""Worker-held speech-to-text models (whisper + pyannote) and their accessors.

The heavy models are loaded once per Celery worker process (see the transcription
worker's worker_process_init) and stored in ``context``. This module owns that
registry so the infra model callers can read it without importing the router.
"""

from typing import TypedDict

from faster_whisper import WhisperModel
from loguru import logger
from pyannote.audio import Pipeline

from mcr_meeting.app.configs.base import (
    PyannoteDiarizationParameters,
    Settings,
    Speech2TextSettings,
)
from mcr_meeting.app.utils.compute_devices import (
    ComputeDevice,
    get_default_gpu_device,
)

settings = Settings()
speech2text_settings = Speech2TextSettings()


class WorkerContext(TypedDict):
    device: ComputeDevice
    model: WhisperModel | None
    diarization_pipeline: Pipeline | None


def load_whisper_model(device: ComputeDevice) -> WhisperModel:
    logger.info("Loading Whisper model...")
    model = WhisperModel(speech2text_settings.STT_MODEL, device=device)

    if not model:
        raise RuntimeError("Failed to load Whisper model")

    logger.info("Model loaded successfully")
    return model


def load_diarization_pipeline(device: ComputeDevice) -> Pipeline:
    logger.info("Loading diarization pipeline...")

    diarization_pipeline = Pipeline.from_pretrained(
        speech2text_settings.DIARIZATION_MODEL,
        use_auth_token=speech2text_settings.HUGGINGFACE_API_KEY,
    )

    if device == ComputeDevice.GPU:
        logger.info("Using GPU for diarization")
        diarization_pipeline.to(get_default_gpu_device())

    diarization_settings = PyannoteDiarizationParameters()
    diarization_pipeline.segmentation.min_duration_off = (
        diarization_settings.min_duration_off
    )
    diarization_pipeline.clustering.min_cluster_size = (
        diarization_settings.min_cluster_size
    )
    diarization_pipeline.clustering.threshold = diarization_settings.threshold

    logger.info("Diarization pipeline loaded successfully")
    return diarization_pipeline


context: WorkerContext = {
    "device": ComputeDevice.CPU,
    "model": None,
    "diarization_pipeline": None,
}


def get_transcription_model() -> WhisperModel:
    if settings.ENV_MODE == "DEV":
        return WhisperModel(speech2text_settings.STT_MODEL)

    transcription_model = context.get("model")
    if transcription_model is None:
        logger.error("Transcription model is None in celery context")
        raise ValueError("Transcription model is None in context.")
    return transcription_model


def get_diarization_pipeline() -> Pipeline:
    if settings.ENV_MODE == "DEV":
        return load_diarization_pipeline(ComputeDevice.CPU)

    diarization_pipeline = context.get("diarization_pipeline")
    if diarization_pipeline is None:
        logger.error("Diarization pipeline is None in celery context")
        raise ValueError("Diarization pipeline is None in context.")
    return diarization_pipeline
