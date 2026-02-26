from typing import Any, Optional

import httpx
from celery.signals import task_failure, task_success
from langfuse import observe
from loguru import logger

from mcr_generation.app.configs.settings import ApiSettings
from mcr_generation.app.schemas.base import BaseReport
from mcr_generation.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    ReportTypes,
)
from mcr_generation.app.services.report_generator import get_generator
from mcr_generation.app.services.utils.input_chunker import chunk_docx_to_document_list
from mcr_generation.app.services.utils.s3_service import get_file_from_s3
from mcr_generation.app.utils.celery_worker import celery_app

api_settings = ApiSettings()


@celery_app.task(name=MCRReportGenerationTasks.REPORT)
@observe(name="generate_report_from_docx_task")
def generate_report_from_docx(
    meeting_id: int,
    transcription_object_filename: str,
    report_type: str = ReportTypes.DECISION_RECORD.value,
) -> BaseReport:
    docx_bytes = get_file_from_s3(transcription_object_filename)
    chunks = chunk_docx_to_document_list(docx_bytes)

    report_type_enum = ReportTypes(report_type)
    generator = get_generator(report_type_enum)
    return generator.generate(chunks)


@task_success.connect
def generate_report_from_docx_success(
    sender: Any, result: BaseReport, **kwargs: Any
) -> None:
    """Handle successful report generation by sending results to mcr-core API.

    Args:
        sender: Celery task that triggered this signal
        result: Generated report with participants and decisions
        **kwargs: Additional keyword arguments from the signal
    """
    logger.info("Report generation success signal received.")

    if not sender.request.args:
        logger.error("Cannot extract meeting_id: request args are empty")
        return

    meeting_id = sender.request.args[0]

    payload_dict = result.model_dump()

    with httpx.Client(base_url=api_settings.MCR_CORE_API_URL) as client:
        response = client.post(
            f"/meetings/{meeting_id}/report/success",
            json=payload_dict,
        )
        response.raise_for_status()


@task_failure.connect
def set_meeting_failed_status_on_error(
    sender: Optional[Any] = None, **kwargs: Any
) -> None:
    pass
