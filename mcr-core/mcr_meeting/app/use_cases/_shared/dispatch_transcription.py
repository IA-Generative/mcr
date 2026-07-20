from loguru import logger

from mcr_meeting.app.infrastructure.celery import (
    enqueue_transcription_pipeline,
    enqueue_transcription_task,
)
from mcr_meeting.app.infrastructure.unleash import FeatureFlag, is_enabled


def dispatch_transcription_task(meeting_id: int, owner_keycloak_uuid: str) -> None:
    enqueue = (
        enqueue_transcription_pipeline
        if _structural_split_enabled()
        else enqueue_transcription_task
    )
    enqueue(meeting_id, owner_keycloak_uuid)


def _structural_split_enabled() -> bool:
    try:
        return is_enabled(FeatureFlag.STRUCTURAL_SPLIT_ENABLED)
    except Exception as e:
        logger.warning(
            "Failed to read STRUCTURAL_SPLIT_ENABLED, enqueueing legacy task: {}", e
        )
        return False
