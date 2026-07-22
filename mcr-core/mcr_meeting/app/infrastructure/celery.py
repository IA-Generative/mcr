from celery import Celery, chain
from celery.canvas import Signature
from loguru import logger

from mcr_meeting.app.configs.base import CelerySettings
from mcr_meeting.app.exceptions.exceptions import TaskCreationException
from mcr_meeting.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    MCRTranscriptionTasks,
)
from mcr_meeting.app.schemas.report_generation import ReportType

celery_settings = CelerySettings()

celery_producer_app = Celery(
    broker=celery_settings.CELERY_BROKER_URL,
)

# Transcription is dispatched as the last statement inside the enclosing DB
# UnitOfWork, so the task is published just before that transaction commits. This
# countdown holds the first task in the broker long enough for the commit to
# become visible, avoiding a worker reading the pre-commit row (e.g. status not
# yet TRANSCRIPTION_PENDING).
_FIRST_TASK_COUNTDOWN_SECONDS = 5

celery_producer_app.conf.task_routes = {
    MCRTranscriptionTasks.select_all_tasks(): {
        "queue": MCRTranscriptionTasks.BASE_NAME
    },
    MCRReportGenerationTasks.select_all_tasks(): {
        "queue": MCRReportGenerationTasks.BASE_NAME
    },
}


def _mark_failed_errback(meeting_id: int, owner_keycloak_uuid: str) -> Signature[None]:
    return celery_producer_app.signature(
        MCRTranscriptionTasks.MARK_TRANSCRIPTION_FAILED.value,
        args=[meeting_id, owner_keycloak_uuid],
        immutable=True,
    )


def enqueue_transcription_task(meeting_id: int, owner_keycloak_uuid: str) -> None:
    try:
        celery_producer_app.send_task(
            MCRTranscriptionTasks.TRANSCRIBE,
            args=[meeting_id, owner_keycloak_uuid],
            countdown=_FIRST_TASK_COUNTDOWN_SECONDS,
            link_error=_mark_failed_errback(meeting_id, owner_keycloak_uuid),
        )
    except Exception as e:
        raise TaskCreationException(
            f"Failed to enqueue transcription task for meeting {meeting_id}"
        ) from e


def enqueue_transcription_pipeline(meeting_id: int, owner_keycloak_uuid: str) -> None:
    args = [meeting_id, owner_keycloak_uuid]
    try:
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
        ).apply_async(
            countdown=_FIRST_TASK_COUNTDOWN_SECONDS,
            link_error=_mark_failed_errback(meeting_id, owner_keycloak_uuid),
        )
    except Exception as e:
        raise TaskCreationException(
            f"Failed to enqueue transcription pipeline for meeting {meeting_id}"
        ) from e


def enqueue_report_generation_task(
    meeting_id: int,
    transcription_object_name: str,
    report_type: ReportType,
    kwargs: dict[str, str | int],
) -> None:
    try:
        celery_producer_app.send_task(
            MCRReportGenerationTasks.REPORT,
            args=[meeting_id, transcription_object_name, report_type],
            kwargs=kwargs,
            countdown=celery_settings.REPORT_START_COUNTDOWN_SECONDS,
        )
    except Exception as exc:
        raise TaskCreationException(
            f"Failed to enqueue report generation task for meeting {meeting_id}"
        ) from exc


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
