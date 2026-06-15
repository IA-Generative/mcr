from mcr_meeting.app.configs.base import EvaluationSettings
from mcr_meeting.app.domain.evaluation_zip import validate_evaluation_zip_structure
from mcr_meeting.app.infrastructure.celery import enqueue_evaluation_task

EVALUATION_SETTINGS = EvaluationSettings()


def evaluate_transcription_from_zip(zip_bytes: bytes) -> None:
    validate_evaluation_zip_structure(
        zip_bytes, EVALUATION_SETTINGS.SUPPORTED_AUDIO_FORMATS
    )
    enqueue_evaluation_task(zip_bytes)
