import asyncio
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, TypedDict, cast

import httpx
import sentry_sdk
from celery import Celery, Task
from celery.signals import task_failure, task_prerun, task_success, worker_process_init
from faster_whisper import WhisperModel
from loguru import logger
from pyannote.audio import Pipeline

from mcr_meeting.app.client.meeting_client import MeetingApiClient
from mcr_meeting.app.configs.base import (
    ApiSettings,
    CelerySettings,
    SentrySettings,
    ServiceSettings,
    Settings,
    Speech2TextSettings,
    TranscriptionWaitingTimeSettings,
)
from mcr_meeting.app.db.db import worker_db_session_context_manager
from mcr_meeting.app.db.transcription_repository import save_transcription

# Import all models to ensure SQLAlchemy relationships are properly resolved
from mcr_meeting.app.models import (  # noqa: F401
    Meeting,
)
from mcr_meeting.app.schemas.celery_types import CelerySignalArgs, MCRTranscriptionTasks
from mcr_meeting.app.services.meeting_to_transcription_service import transcribe_meeting
from mcr_meeting.app.utils.compute_devices import (
    ComputeDevice,
    get_gpu_name,
    is_gpu_available,
)
from mcr_meeting.app.utils.load_speech_to_text_model import (
    load_diarization_pipeline,
    load_whisper_model,
)
from mcr_meeting.evaluation.asr_evaluation_pipeline import ASREvaluationPipeline
from mcr_meeting.evaluation.eval_types import EvaluationInput, TranscriptionOutput
from mcr_meeting.setup.logger import setup_logging

setup_logging()

s2t_settings = Speech2TextSettings()
celerySettings = CelerySettings()
service_settings = ServiceSettings()
api_settings = ApiSettings()
transcription_waiting_time_settings = TranscriptionWaitingTimeSettings()
sentrySettings = SentrySettings()
settings = Settings()

sentry_sdk.init(
    dsn=sentrySettings.SENTRY_TRANSCRIPTION_DSN,
    send_default_pii=sentrySettings.SEND_DEFAULT_PII,
    traces_sample_rate=sentrySettings.TRACES_SAMPLE_RATE,
    environment=settings.ENV_MODE,
    ignore_errors=[],
)

celery_worker = Celery(
    "transcriber",
    broker=celerySettings.CELERY_BROKER_URL,
    backend=celerySettings.CELERY_BACKEND_URL,
)

celery_worker.conf.task_track_started = True
celery_worker.conf.result_expires = 3600
celery_worker.conf.task_default_queue = MCRTranscriptionTasks.BASE_NAME

celery_worker.conf.worker_concurrency = 1
celery_worker.conf.worker_prefetch_multiplier = 1
celery_worker.conf.task_acks_late = True


class WorkerContext(TypedDict):
    device: ComputeDevice
    model: WhisperModel | None
    diarization_pipeline: Pipeline | None


context: WorkerContext = {
    "device": ComputeDevice.CPU,
    "model": None,
    "diarization_pipeline": None,
}


@worker_process_init.connect
def initialize_worker(**kwarg: Any) -> None:  # type: ignore[explicit-any]
    """
    Initialize worker processes with model and device setup.
    This worker consume both `transcribe` and `evaluate` tasks.
    Both theses task require heavy computations with high CPU and GPU demands
    """
    global context

    logger.debug("======== Initializating Celery worker processes =========")

    if is_gpu_available():
        logger.info("GPU is available")
        logger.info("Using device: {}", get_gpu_name())
        context["device"] = ComputeDevice.GPU
    else:
        logger.trace("GPU not available — running on CPU")
        context["device"] = ComputeDevice.CPU

    context["model"] = load_whisper_model(context["device"])
    context["diarization_pipeline"] = load_diarization_pipeline(context["device"])

    logger.info("======== Celery worker processes initialization done =========")


@celery_worker.task(name=MCRTranscriptionTasks.TRANSCRIBE, max_retries=3)
def transcribe(meeting_id: int) -> None:
    with worker_db_session_context_manager() as db:
        meeting = db.get(Meeting, meeting_id)

        if meeting is None:
            logger.error("Meeting not found: {}", meeting_id)
            return

        client = MeetingApiClient(str(meeting.owner.keycloak_uuid))

        transcription_data = transcribe_meeting(meeting_id=meeting_id)
        logger.debug("transcription data {}", transcription_data)

        if transcription_data:
            save_transcription(transcription_data)
            asyncio.run(client.end_transcription(meeting_id))
            logger.info("Meeting {} updated to TRANSCRIPTION_DONE", meeting_id)
        else:
            asyncio.run(client.fail_transcription(meeting_id))
            logger.error("Meeting {} updated to TRANSCRIPTION_FAILED", meeting_id)
        logger.info("task processed !")


@task_prerun.connect(sender=transcribe)
def set_meeting_in_progress_status(
    **kwargs: CelerySignalArgs,
) -> None:
    typed_kwargs = cast(CelerySignalArgs, kwargs)
    with worker_db_session_context_manager() as db:
        meeting_id = typed_kwargs["args"][0]
        meeting = db.get(Meeting, meeting_id)

        if meeting is None:
            logger.error("Meeting not found: {}", meeting_id)
            return

        client = MeetingApiClient(str(meeting.owner.keycloak_uuid))

        asyncio.run(client.start_transcription(meeting_id))
        logger.info("Starting transcription for meeting ID: {}", meeting_id)


@task_success.connect(sender=transcribe)
def generate_transcription_success(  # type: ignore[explicit-any]
    sender: Task[Any, Any],
    result: Any,
    **kwargs: Any,
) -> None:
    meeting_id = None
    if "args" in kwargs and kwargs["args"]:
        meeting_id = kwargs["args"][0]
    elif (
        hasattr(sender, "request")
        and hasattr(sender.request, "args")
        and sender.request.args
    ):
        meeting_id = sender.request.args[0]

    if meeting_id is None:
        logger.error("Unable to retrieve meeting_id in the success signal")
        return

    logger.info("Transcription generation success signal received {}.", meeting_id)
    with httpx.Client(base_url=service_settings.CORE_SERVICE_BASE_URL) as client:
        client.post(
            f"{api_settings.MEETING_API_PREFIX}/{meeting_id}/transcription/success"
        ).raise_for_status()


@task_failure.connect(sender=transcribe)
def set_meeting_failed_status_on_error(**kwargs: Any) -> None:  # type: ignore[explicit-any]
    typed_kwargs = cast(CelerySignalArgs, kwargs)

    with worker_db_session_context_manager() as db:
        meeting_id = typed_kwargs["args"][0]
        meeting = db.get(Meeting, meeting_id)

        if meeting is None:
            logger.error("Meeting not found: {}", meeting_id)
            return

        client = MeetingApiClient(str(meeting.owner.keycloak_uuid))
        asyncio.run(client.fail_transcription(meeting_id))

        logger.error("Meeting {} updated to TRANSCRIPTION_FAILED", meeting_id)


@celery_worker.task(name=MCRTranscriptionTasks.EVALUATE, max_retries=3)
def evaluate(zip_data: bytes) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with zipfile.ZipFile(BytesIO(zip_data)) as z:
            z.extractall(temp_path)

        logger.info("Extracted zip file to temporary directory: {}", temp_path)

        extracted_files = list(temp_path.rglob("*"))
        logger.info(
            "Extracted files in {}: {}", temp_path, [str(f) for f in extracted_files]
        )

        base_path = temp_path / "inputs"
        audio_dir = base_path / "raw_audios"
        reference_dir = base_path / "reference_transcripts"

        if not audio_dir.exists() or not reference_dir.exists():
            logger.error(
                "Could not find 'raw_audios' or 'reference_transcripts' in {}",
                base_path,
            )
            raise ValueError(
                "Zip file must contain 'raw_audios' and 'reference_transcripts' folders within an 'inputs' directory.",
            )

        evaluation_inputs = []
        for audio_file in audio_dir.glob("*.mp3"):
            uid = audio_file.stem
            audio_bytes = BytesIO(audio_file.read_bytes())

            ref_json_path = reference_dir / f"{uid}.json"
            if ref_json_path.exists():
                with open(ref_json_path, "r") as f:
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

        pipeline = ASREvaluationPipeline(inputs=evaluation_inputs)
        output_dir = temp_path / "outputs"
        output_dir.mkdir()

        pipeline.run_evaluation(output_dir=output_dir)
