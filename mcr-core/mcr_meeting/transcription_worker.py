import asyncio
import tempfile
import zipfile
from functools import partial
from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_meeting.app.configs.base import EvaluationSettings
from mcr_meeting.app.infrastructure import s3
from mcr_meeting.app.infrastructure.celery_consumer import (
    MeetingPipelineTask,
    celery_worker,
)
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.langfuse import init_langfuse
from mcr_meeting.app.infrastructure.meeting_api_client import MeetingApiClient
from mcr_meeting.app.infrastructure.sentry import init_sentry
from mcr_meeting.app.infrastructure.speech_to_text_models import (
    get_diarization_pipeline,
    get_transcription_model,
)
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
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
from mcr_meeting.app.utils.sentry_context import (
    gather_meeting_context,
    set_sentry_meeting_context,
)
from mcr_meeting.evaluation.asr.evaluation_pipeline import ASREvaluationPipeline
from mcr_meeting.evaluation.asr.types import EvaluationInput, TranscriptionOutput

init_sentry()
init_langfuse()

SUPPORTED_AUDIO_FORMATS_FOR_EVALUATION = EvaluationSettings().SUPPORTED_AUDIO_FORMATS


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
    max_retries=3,
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
    max_retries=3,
)
def diarize(meeting_id: int, owner_keycloak_uuid: str) -> None:
    asyncio.run(MeetingApiClient(owner_keycloak_uuid).start_transcription(meeting_id))
    run_diarization(meeting_id, DiarizationProcessor(get_diarization_pipeline))
    logger.info("Diarization completed for meeting {}", meeting_id)


@celery_worker.task(
    base=TranscriptionPipelineTask,
    name=MCRTranscriptionTasks.TRANSCRIBE_CHUNKS,
    max_retries=3,
)
def transcribe_chunks(meeting_id: int, owner_keycloak_uuid: str) -> None:
    run_transcribe_chunks(meeting_id, TranscriptionProcessor(get_transcription_model))
    logger.info("Chunk transcription completed for meeting {}", meeting_id)


@celery_worker.task(
    base=TranscriptionPipelineTask,
    name=MCRTranscriptionTasks.FINALIZE_TRANSCRIPTION,
    max_retries=3,
)
def finalize_transcription(meeting_id: int, owner_keycloak_uuid: str) -> None:
    run_finalize_transcription(meeting_id)
    _mark_success(meeting_id, owner_keycloak_uuid)


def _run_evaluation(zip_data: bytes) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with zipfile.ZipFile(BytesIO(zip_data)) as z:
            z.extractall(temp_path)

        logger.info("Extracted zip file to temporary directory: {}", temp_path)

        extracted_files = list(temp_path.rglob("*"))
        logger.info(
            "Extracted files in {}: {}", temp_path, [str(f) for f in extracted_files]
        )

        # Find any directory that contains both raw_audios and reference_transcripts
        base_path = None
        for candidate in [temp_path, *temp_path.iterdir()]:
            if (
                candidate.is_dir()
                and (candidate / "raw_audios").exists()
                and (candidate / "reference_transcripts").exists()
            ):
                base_path = candidate
                break

        if base_path is None:
            logger.error(
                "Could not find 'raw_audios' and 'reference_transcripts' directories in the zip file."
            )
            raise ValueError(
                "Zip file must contain 'raw_audios' and 'reference_transcripts' folders (at any root level).",
            )

        audio_dir = base_path / "raw_audios"
        reference_dir = base_path / "reference_transcripts"

        evaluation_inputs = []
        audio_files = [
            f
            for fmt in SUPPORTED_AUDIO_FORMATS_FOR_EVALUATION
            for f in audio_dir.glob(f"*.{fmt}")
        ]
        for audio_file in audio_files:
            uid = audio_file.stem
            audio_bytes = BytesIO(audio_file.read_bytes())

            ref_json_path = reference_dir / f"{uid}.json"
            if ref_json_path.exists():
                with open(ref_json_path) as f:
                    reference_transcription = TranscriptionOutput.model_validate_json(
                        f.read()
                    )
            if not isinstance(reference_transcription, TranscriptionOutput):
                logger.warning(
                    "Reference transcription not found for {}, skipping this file.", uid
                )
                continue
            evaluation_inputs.append(
                EvaluationInput(
                    uid=uid,
                    audio_path=audio_file,
                    audio_bytes=audio_bytes,
                    reference_transcription=reference_transcription,
                )
            )

        if not evaluation_inputs:
            raise ValueError("No valid evaluation inputs found in the zip file.")

        pipeline = ASREvaluationPipeline(
            inputs=evaluation_inputs,
            transcribe_audio=partial(
                run_speech_to_text,
                diarization_processor=DiarizationProcessor(get_diarization_pipeline),
                transcription_processor=TranscriptionProcessor(get_transcription_model),
            ),
        )
        output_dir = temp_path / "outputs"
        output_dir.mkdir()

        pipeline.run_evaluation(output_dir=output_dir)


@celery_worker.task(name=MCRTranscriptionTasks.EVALUATE, max_retries=3)
def evaluate(zip_data: bytes) -> None:
    _run_evaluation(zip_data)


@celery_worker.task(name=MCRTranscriptionTasks.EVALUATE_FROM_S3, max_retries=3)
def evaluate_from_s3(zip_name: str) -> None:
    object_name = s3.get_evaluation_dataset_object_name(zip_name)
    logger.info("Downloading evaluation zip from S3: {}", object_name)
    zip_buffer = s3.get_file_from_s3(object_name)
    _run_evaluation(zip_buffer.getvalue())
