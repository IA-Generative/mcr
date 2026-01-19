from typing import Any, Optional

import httpx
from celery.signals import task_failure, task_success
from langfuse import observe
from loguru import logger

from mcr_generation.app.configs.settings import ApiSettings
from mcr_generation.app.schemas.base import Report
from mcr_generation.app.schemas.celery_types import MCRReportGenerationTasks
from mcr_generation.app.services.sections import (
    MapReduceTopics,
    RefineIntent,
    RefineNextMeeting,
    RefineParticipants,
    format_next_meeting_for_report,
)
from mcr_generation.app.services.utils.input_chunker import chunk_docx_to_document_list
from mcr_generation.app.services.utils.s3_service import get_file_from_s3
from mcr_generation.app.utils.celery_worker import celery_app

api_settings = ApiSettings()


@celery_app.task(name=MCRReportGenerationTasks.REPORT)
@observe(name="generate_report_from_docx_task")
def generate_report_from_docx(
    meeting_id: int,
    transcription_object_filename: str,
) -> Report:
    refine_intent = RefineIntent()
    refine_participants = RefineParticipants()
    refine_next_meeting = RefineNextMeeting()
    docx_bytes = get_file_from_s3(transcription_object_filename)
    chunks = chunk_docx_to_document_list(docx_bytes)
    intent = refine_intent.init_then_refine(chunks)
    participants = refine_participants.init_then_refine(chunks)
    next_meeting = refine_next_meeting.init_then_refine(chunks)

    map_reduce = MapReduceTopics(
        meeting_subject=intent.title,
        speaker_mapping=participants,
    )
    content = map_reduce.map_reduce_all_steps(chunks)

    report = Report(
        title=intent.title,
        objective=intent.objective,
        next_meeting=format_next_meeting_for_report(next_meeting),
        next_steps=content.next_steps,
        participants=participants.participants,
        topics_with_decision=content.topics,
    )

    return report


@task_success.connect
def generate_report_from_docx_success(
    sender: Any, result: Report, **kwargs: Any
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

    payload_dict = {
        "next_steps": result.next_steps,
        "topics_with_decision": [
            topic.model_dump() for topic in result.topics_with_decision
        ],
        "header": {
            "title": result.title,
            "objective": result.objective,
            "next_meeting": result.next_meeting,
            "participants": [
                p.model_dump(exclude={"association_justification"})
                for p in result.participants
            ],
        },
    }

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
