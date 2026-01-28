from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.orchestrators.meeting_orchestrator import get_meeting
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    complete_report,
    start_report, fail_report,
)
from mcr_meeting.app.schemas.report_generation import ReportGenerationResponse
from mcr_meeting.app.services.report_task_service import (
    get_formatted_report_from_s3,
)
from mcr_meeting.app.utils.filename_header import create_safe_filename_header
from mcr_meeting.app.utils.files_mime_types import DOCX_MIME_TYPE

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Meetings", "Report"],
)


@router.get("/{meeting_id}/report")
async def get_meeting_report(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> StreamingResponse:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting

    """

    meeting = get_meeting(
        meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid
    )

    docx_buffer = get_formatted_report_from_s3(meeting)
    filename = f"compte_rendu_{meeting.name}.docx"
    headers = create_safe_filename_header(filename)

    return StreamingResponse(
        docx_buffer,
        media_type=DOCX_MIME_TYPE,
        headers=headers,
    )


@router.post("/{meeting_id}/report")
async def generate_meeting_report(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> None:
    """
    Create the report

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        None

    """
    start_report(meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid)


@router.post("/{meeting_id}/report/success")
async def generate_meeting_report_success(
    meeting_id: int,
    report_response: ReportGenerationResponse,
) -> None:
    complete_report(meeting_id=meeting_id, report_response=report_response)


@router.post("/{meeting_id}/report/failure")
async def generate_meeting_report_failure(
    meeting_id: int,
) -> None:
    fail_report(meeting_id=meeting_id)
