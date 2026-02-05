"""Utility functions for Celery worker initialization."""

from faster_whisper import WhisperModel  # type: ignore[import]
from loguru import logger
from pyannote.audio import Pipeline

from mcr_meeting.app.configs.base import Speech2TextSettings
from mcr_meeting.app.utils.compute_devices import ComputeDevice

s2t_settings = Speech2TextSettings()


def load_whisper_model(device: ComputeDevice) -> WhisperModel:
    """Load Whisper transcription model.

    Args:
        device: The compute device to use (CPU or GPU)

    Returns:
        WhisperModel: The loaded Whisper model

    Raises:
        RuntimeError: If the model fails to load
    """
    logger.info("Loading Whisper model...")
    model = WhisperModel(s2t_settings.STT_MODEL, device=device)

    if not model:
        raise RuntimeError("Failed to load Whisper model")

    logger.info("Model loaded successfully")
    return model


def load_diarization_pipeline(device: ComputeDevice) -> Pipeline:
    """Load speaker diarization pipeline.

    Args:
        device: The compute device to use (CPU or GPU)

    Returns:
        Pipeline: The configured diarization pipeline
    """
    logger.info("Loading diarization pipeline...")

    diarization_pipeline = Pipeline.from_pretrained(
        s2t_settings.DIARIZATION_MODEL,
        use_auth_token=s2t_settings.HUGGINGFACE_API_KEY,
    )

    if device == ComputeDevice.GPU:
        logger.info("Using GPU for diarization")
        from mcr_meeting.app.utils.compute_devices import get_default_gpu_device

        diarization_pipeline.to(get_default_gpu_device())

    # Configure diarization hyperparameters
    from mcr_meeting.app.configs.base import PyannoteDiarizationParameters

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
