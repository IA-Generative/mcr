from typing import Any

from celery.signals import task_failure, task_prerun, task_success
from langfuse import observe
from loguru import logger

from mcr_generation.app.client.core_api_client import CoreApiClient
from mcr_generation.app.client.meeting_client import MeetingApiClient
from mcr_generation.app.configs.settings import LangfuseSettings
from mcr_generation.app.schemas.base import BaseReport
from mcr_generation.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    ReportTypes,
    extract_report_task_args,
)
from mcr_generation.app.services.report_generator import get_generator
from mcr_generation.app.services.utils.input_chunker import chunk_docx_to_document_list
from mcr_generation.app.services.utils.s3_service import get_file_from_s3
from mcr_generation.app.utils.celery_worker import celery_app
from mcr_generation.app.utils.langfuse_observability import (
    record_chunking_metadata,
    record_report_trace_context,
)
from mcr_generation.app.utils.sentry_context import (
    gather_meeting_context,
    set_sentry_meeting_context,
)

langfuse_settings = LangfuseSettings()


@celery_app.task(name=MCRReportGenerationTasks.REPORT)
@observe(name="generate_report_from_docx_task")
def generate_report_from_docx(
    meeting_id: int,
    transcription_object_filename: str,
    report_type: str = ReportTypes.DECISION_RECORD.value,
    owner_keycloak_uuid: str | None = None,
) -> BaseReport:
    record_report_trace_context(
        meeting_id=meeting_id,
        transcription_object_filename=transcription_object_filename,
        report_type=report_type,
        env_mode=langfuse_settings.ENV_MODE,
    )

    docx_bytes = get_file_from_s3(transcription_object_filename)
    chunks = chunk_docx_to_document_list(docx_bytes)

    record_chunking_metadata(
        chunk_count=len(chunks),
        total_chars=sum(len(c.text) for c in chunks),
    )

    report_type_enum = ReportTypes(report_type)
    generator = get_generator(report_type_enum)
    return generator.generate(chunks)


@task_prerun.connect(sender=generate_report_from_docx)
def set_sentry_context_before_report_generation(**kwargs: Any) -> None:
    task_args = extract_report_task_args(kwargs)

    client = MeetingApiClient(task_args.owner_keycloak_uuid)
    meeting_context = gather_meeting_context(
        task_args.meeting_id, task_args.owner_keycloak_uuid, client
    )
    set_sentry_meeting_context(meeting_context)


@task_success.connect
def generate_report_from_docx_success(
    sender: Any, result: BaseReport, **kwargs: Any
) -> None:
    """Handle successful report generation by sending results to mcr-core API."""
    logger.info("Report generation success signal received.")

    if not sender.request.args:
        logger.error("Cannot extract meeting_id: request args are empty")
        return

    meeting_id = sender.request.args[0]

    CoreApiClient().mark_report_success(meeting_id=meeting_id, report=result)


@task_failure.connect
def set_meeting_failed_status_on_error(
    sender: Any | None = None, **kwargs: Any
) -> None:
    meeting_id: int | None = None
    args = kwargs.get("args")
    if args:
        meeting_id = args[0]
    elif sender is not None and hasattr(sender, "request") and sender.request.args:
        meeting_id = sender.request.args[0]

    if meeting_id is None:
        logger.error("Unable to extract meeting_id from signal args")
        return

    logger.error("Meeting {} updated to REPORT_FAILED", meeting_id)

    CoreApiClient().mark_report_failure(meeting_id=meeting_id)
