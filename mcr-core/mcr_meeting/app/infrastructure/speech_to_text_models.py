"""Worker-held speech-to-text models (whisper + pyannote) and their accessors.

The heavy models are loaded once per Celery worker process (see the transcription
worker's worker_process_init) and stored in ``context``. This module owns that
registry so the infra model callers can read it without importing the router.
"""

from typing import TypedDict

from faster_whisper import WhisperModel
from loguru import logger
from pyannote.audio import Pipeline

from mcr_meeting.app.configs.base import Settings, Speech2TextSettings
from mcr_meeting.app.utils.compute_devices import ComputeDevice
from mcr_meeting.app.utils.load_speech_to_text_model import load_diarization_pipeline

settings = Settings()
speech2text_settings = Speech2TextSettings()


class WorkerContext(TypedDict):
    device: ComputeDevice
    model: WhisperModel | None
    diarization_pipeline: Pipeline | None


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
