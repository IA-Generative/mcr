import asyncio
from collections.abc import Callable
from functools import partial
from io import BytesIO

from loguru import logger

from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.celery_consumer import (
    MeetingPipelineTask,
    RetryableInfraTask,
    celery_worker,
)
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.langfuse import init_langfuse
from mcr_meeting.app.infrastructure.meeting_api_client import MeetingApiClient
from mcr_meeting.app.infrastructure.sentry import (
    gather_meeting_context,
    init_sentry,
    set_sentry_meeting_context,
)
from mcr_meeting.app.infrastructure.speech_to_text_models import (
    get_diarization_pipeline,
    get_transcription_model,
)
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    SpeakerTranscription,
)
from mcr_meeting.app.use_cases.run_evaluation_from_zip import run_evaluation_from_zip
from mcr_meeting.app.use_cases.transcription.run_diarization import run_diarization
from mcr_meeting.app.use_cases.transcription.run_finalize_transcription import (
    run_finalize_transcription,
)
from mcr_meeting.app.use_cases.transcription.run_mark_transcription_failed import (
    run_mark_transcription_failed,
)
from mcr_meeting.app.use_cases.transcription.run_speech_to_text import (
    run_speech_to_text,
)
from mcr_meeting.app.use_cases.transcription.run_transcribe_chunks import (
    run_transcribe_chunks,
)

init_sentry()
init_langfuse()


def run_transcription_in_task(meeting_id: int, owner_keycloak_uuid: str) -> None:
    run_diarization(meeting_id, DiarizationProcessor(get_diarization_pipeline))
    run_transcribe_chunks(meeting_id, TranscriptionProcessor(get_transcription_model))
    speaker_transcriptions = run_finalize_transcription(meeting_id)
    _mark_success(meeting_id, owner_keycloak_uuid, speaker_transcriptions)
    logger.info("Transcription completed for meeting {}", meeting_id)


def _mark_success(
    meeting_id: int,
    owner_keycloak_uuid: str,
    speaker_transcriptions: list[SpeakerTranscription] | None = None,
) -> None:
    result = (
        [item.model_dump() for item in speaker_transcriptions]
        if speaker_transcriptions is not None
        else None
    )
    asyncio.run(
        MeetingApiClient(owner_keycloak_uuid).mark_transcription_as_success(
            meeting_id, transcription_data=result
        )
    )
    logger.info("Meeting {} updated to TRANSCRIPTION_DONE", meeting_id)


class TranscriptionPipelineTask(MeetingPipelineTask):
    def set_task_context(self, meeting_id: int, owner_keycloak_uuid: str) -> None:
        client = MeetingApiClient(owner_keycloak_uuid)
        meeting_context = gather_meeting_context(
            meeting_id, owner_keycloak_uuid, client
        )
        set_sentry_meeting_context(meeting_context)


@celery_worker.task(name=MCRTranscriptionTasks.MARK_TRANSCRIPTION_FAILED)
def mark_transcription_failed(meeting_id: int, owner_keycloak_uuid: str) -> None:
    try:
        run_mark_transcription_failed(meeting_id, owner_keycloak_uuid)
    except Exception:
        logger.exception(
            "Failed to mark meeting {} as TRANSCRIPTION_FAILED", meeting_id
        )


@celery_worker.task(
    base=TranscriptionPipelineTask,
    name=MCRTranscriptionTasks.TRANSCRIBE,
)
def transcribe(meeting_id: int, owner_keycloak_uuid: str) -> None:
    """Legacy monolithic task, kept while STRUCTURAL_SPLIT_ENABLED is off and
    already-queued messages may still arrive. New enqueues go through the
    diarize → transcribe_chunks → finalize_transcription chain built core-side.
    """
    asyncio.run(MeetingApiClient(owner_keycloak_uuid).start_transcription(meeting_id))
    run_transcription_in_task(meeting_id, owner_keycloak_uuid)


@celery_worker.task(
    base=TranscriptionPipelineTask,
    name=MCRTranscriptionTasks.DIARIZE,
)
def diarize(meeting_id: int, owner_keycloak_uuid: str) -> None:
    asyncio.run(MeetingApiClient(owner_keycloak_uuid).start_transcription(meeting_id))
    run_diarization(meeting_id, DiarizationProcessor(get_diarization_pipeline))
    logger.info("Diarization completed for meeting {}", meeting_id)


@celery_worker.task(
    base=TranscriptionPipelineTask,
    name=MCRTranscriptionTasks.TRANSCRIBE_CHUNKS,
)
def transcribe_chunks(meeting_id: int, owner_keycloak_uuid: str) -> None:
    run_transcribe_chunks(meeting_id, TranscriptionProcessor(get_transcription_model))
    logger.info("Chunk transcription completed for meeting {}", meeting_id)


@celery_worker.task(
    base=TranscriptionPipelineTask,
    name=MCRTranscriptionTasks.FINALIZE_TRANSCRIPTION,
)
def finalize_transcription(meeting_id: int, owner_keycloak_uuid: str) -> None:
    run_finalize_transcription(meeting_id)
    _mark_success(meeting_id, owner_keycloak_uuid)


def _evaluation_transcribe_audio() -> Callable[
    [BytesIO], list[DiarizedTranscriptionSegment]
]:
    return partial(
        run_speech_to_text,
        diarization_processor=DiarizationProcessor(get_diarization_pipeline),
        transcription_processor=TranscriptionProcessor(get_transcription_model),
    )


@celery_worker.task(
    base=RetryableInfraTask,
    name=MCRTranscriptionTasks.EVALUATE,
)
def evaluate(zip_data: bytes) -> None:
    run_evaluation_from_zip(zip_data, _evaluation_transcribe_audio())


@celery_worker.task(
    base=RetryableInfraTask,
    name=MCRTranscriptionTasks.EVALUATE_FROM_S3,
)
def evaluate_from_s3(zip_name: str) -> None:
    object_name = s3.get_evaluation_dataset_object_name(zip_name)
    logger.info("Downloading evaluation zip from S3: {}", object_name)
    zip_buffer = s3.get_file_from_s3(object_name)
    run_evaluation_from_zip(zip_buffer.getvalue(), _evaluation_transcribe_audio())
