"""Worker-held speech-to-text models (whisper + pyannote) and their accessors.

The heavy models are lazy-loaded at first use and cached for the lifetime of
the worker process. API-mode workers never call the accessors, so they boot
fast and never reserve the GPU. The router injects the accessors into the
infra processors — infra never loads models directly.
"""

from functools import lru_cache

from faster_whisper import WhisperModel
from loguru import logger
from pyannote.audio import Pipeline

from mcr_meeting.app.configs.base import (
    PyannoteDiarizationParameters,
    Speech2TextSettings,
)
from mcr_meeting.app.infrastructure.compute_devices import (
    ComputeDevice,
    get_default_gpu_device,
    get_gpu_name,
    is_gpu_available,
)

speech2text_settings = Speech2TextSettings()


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


def _resolve_device() -> ComputeDevice:
    if is_gpu_available():
        logger.info("Loading speech-to-text model on GPU: {}", get_gpu_name())
        return ComputeDevice.GPU
    logger.info("GPU not available — loading speech-to-text model on CPU")
    return ComputeDevice.CPU


@lru_cache(maxsize=1)
def get_transcription_model() -> WhisperModel:
    return load_whisper_model(_resolve_device())


@lru_cache(maxsize=1)
def get_diarization_pipeline() -> Pipeline:
    return load_diarization_pipeline(_resolve_device())
