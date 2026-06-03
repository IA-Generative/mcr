from typing import Any

from celery.signals import task_failure, task_prerun, task_success
from langfuse import observe
from loguru import logger

from mcr_generation.app.client.core_api_client import CoreApiClient
from mcr_generation.app.client.meeting_client import MeetingApiClient
from mcr_generation.app.configs.settings import LangfuseSettings
from mcr_generation.app.schemas.base import (
    BaseReport,
    CustomMarkdownReport,
    NarrativeSynthesis,
)
from mcr_generation.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    ReportTypes,
    extract_report_task_args,
)
from mcr_generation.app.services.report_generator import create_report_generator
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
    deliverable_id: int | None = None,
    owner_keycloak_uuid: str | None = None,
    notes_content: str | None = None,
    custom_prompt: str | None = None,
) -> BaseReport | CustomMarkdownReport | NarrativeSynthesis:
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

    generator = create_report_generator(report_type_enum, custom_prompt=custom_prompt)
    report = generator.generate(chunks, notes_content=notes_content)

    return report


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
    sender: Any,
    result: BaseReport | CustomMarkdownReport | NarrativeSynthesis,
    **kwargs: Any,
) -> None:
    """Handle successful report generation by sending results to mcr-core API."""
    logger.info("Report generation success signal received.")

    try:
        task_args = extract_report_task_args(sender=sender)
    except ValueError:
        logger.error("Cannot extract meeting_id: request args are empty")
        return

    client = CoreApiClient()
    client.mark_deliverable_success(
        deliverable_id=task_args.deliverable_id, report=result
    )


@task_failure.connect
def set_meeting_failed_status_on_error(
    sender: Any | None = None, **kwargs: Any
) -> None:
    try:
        task_args = extract_report_task_args(kwargs, sender=sender)
    except ValueError:
        logger.error("Unable to extract meeting_id from signal args")
        return

    logger.error("Meeting {} updated to REPORT_FAILED", task_args.meeting_id)

    client = CoreApiClient()
    client.mark_deliverable_failure(deliverable_id=task_args.deliverable_id)
