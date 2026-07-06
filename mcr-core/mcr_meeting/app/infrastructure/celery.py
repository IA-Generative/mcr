from celery import Celery, chain
from loguru import logger

from mcr_meeting.app.configs.base import CelerySettings
from mcr_meeting.app.exceptions.exceptions import TaskCreationException
from mcr_meeting.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    MCRTranscriptionTasks,
)

celery_settings = CelerySettings()

celery_producer_app = Celery(
    broker=celery_settings.CELERY_BROKER_URL,
)

celery_producer_app.conf.task_routes = {
    MCRTranscriptionTasks.select_all_tasks(): {
        "queue": MCRTranscriptionTasks.BASE_NAME
    },
    MCRReportGenerationTasks.select_all_tasks(): {
        "queue": MCRReportGenerationTasks.BASE_NAME
    },
}


def enqueue_transcription_task(meeting_id: int, owner_keycloak_uuid: str) -> None:
    try:
        celery_producer_app.send_task(
            MCRTranscriptionTasks.TRANSCRIBE,
            args=[meeting_id, owner_keycloak_uuid],
        )
    except Exception as e:
        raise TaskCreationException(
            f"Failed to enqueue transcription task for meeting {meeting_id}"
        ) from e


def enqueue_transcription_pipeline(meeting_id: int, owner_keycloak_uuid: str) -> None:
    args = [meeting_id, owner_keycloak_uuid]
    try:
        # immutable: sans ça le worker préfixe le retour du maillon précédent
        # aux args du suivant (équivalent name-based du .si()).
        chain(
            celery_producer_app.signature(
                MCRTranscriptionTasks.DIARIZE.value, args=args, immutable=True
            ),
            celery_producer_app.signature(
                MCRTranscriptionTasks.TRANSCRIBE_CHUNKS.value, args=args, immutable=True
            ),
            celery_producer_app.signature(
                MCRTranscriptionTasks.FINALIZE_TRANSCRIPTION.value,
                args=args,
                immutable=True,
            ),
        ).apply_async()
    except Exception as e:
        raise TaskCreationException(
            f"Failed to enqueue transcription pipeline for meeting {meeting_id}"
        ) from e


def enqueue_evaluation_task(zip_bytes: bytes) -> None:
    try:
        celery_producer_app.send_task(MCRTranscriptionTasks.EVALUATE, args=[zip_bytes])
        logger.info("Evaluation task created")
    except Exception as exc:
        logger.error("Error creating evaluation task: {}", exc)
        raise TaskCreationException(str(exc)) from exc


def enqueue_evaluation_from_s3_task(zip_name: str) -> None:
    try:
        celery_producer_app.send_task(
            MCRTranscriptionTasks.EVALUATE_FROM_S3, args=[zip_name]
        )
        logger.info("Evaluation from S3 task created for: {}", zip_name)
    except Exception as exc:
        logger.error("Error creating evaluation from S3 task: {}", exc)
        raise TaskCreationException(str(exc)) from exc
