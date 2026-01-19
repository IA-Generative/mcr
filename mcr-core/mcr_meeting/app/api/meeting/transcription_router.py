from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import (
    router_db_session_context_manager,
)
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    complete_transcription,
    fail_transcription,
    init_transcription,
    start_transcription,
)
from mcr_meeting.app.orchestrators.transcription_orchestrator import (
    get_or_create_transcription_docx,
    get_transcription_waiting_time,
    upload_transcription_docx,
)
from mcr_meeting.app.schemas.transcription_queue_schema import (
    TranscriptionQueueStatusResponse,
)
from mcr_meeting.app.services.send_email_service import (
    send_transcription_generation_success_email,
)
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)
from mcr_meeting.app.utils.files_mime_types import DOCX_MIME_TYPE

api_settings = ApiSettings()

router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Meetings", "Transcription"],
)


@router.post("/{meeting_id}/transcription")
async def retrieve_or_create_formatted_meeting_transcription(
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

    result = await get_or_create_transcription_docx(
        meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid
    )

    url_encoded_filename = quote(result.filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{url_encoded_filename}"
    }

    return StreamingResponse(
        result.buffer,
        media_type=DOCX_MIME_TYPE,
        headers=headers,
    )


@router.put("/{meeting_id}/transcription", status_code=status.HTTP_204_NO_CONTENT)
async def upload_meeting_transcription(
    file: UploadFile,
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> None:
    """
    Adds the modified transcription with a new version to a given meeting

    Args:
        meeting_id (int): The ID of the meeting.
        file: Transcription DOCX file

    Returns:
        204 if the transcription has been added

    """
    if not (file.content_type and file.content_type == DOCX_MIME_TYPE):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Please upload a DOCX file.",
        )

    upload_transcription_docx(
        meeting_id=meeting_id, file=file, user_keycloak_uuid=x_user_keycloak_uuid
    )


@router.post("/{meeting_id}/transcription/init", status_code=status.HTTP_204_NO_CONTENT)
async def init_transcription_task(meeting_id: int) -> None:
    init_transcription(meeting_id=meeting_id)


@router.post(
    "/{meeting_id}/transcription/start", status_code=status.HTTP_204_NO_CONTENT
)
async def start_transcription_task(meeting_id: int) -> None:
    start_transcription(meeting_id=meeting_id)


@router.post("/{meeting_id}/transcription/fail", status_code=status.HTTP_204_NO_CONTENT)
async def fail_transcription_task(meeting_id: int) -> None:
    fail_transcription(meeting_id=meeting_id)


@router.post("/{meeting_id}/transcription/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_transcription_task(meeting_id: int) -> None:
    complete_transcription(meeting_id=meeting_id)


@router.post("/{meeting_id}/transcription/success")
async def generate_meeting_transcription_success(
    meeting_id: int,
) -> None:
    send_transcription_generation_success_email(meeting_id=meeting_id)


@router.get("/{meeting_id}/transcription/wait-time")
async def get_meeting_remaining_waiting_time(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> TranscriptionQueueStatusResponse:
    """
    Get the remaining waiting time for the transcription of a specific meeting.

    Calculate the remaining time based on the meeting's estimated end date minus current time.

    Args:
        meeting_id: The ID of the meeting for which to calculate the remaining waiting time
        x_user_keycloak_uuid: UUID de l'utilisateur authentifié

    Returns:
        TranscriptionQueueStatusResponse: Contains the remaining waiting time in minutes

    Raises:
        HTTPException: 404 if the meeting does not exist
        HTTPException: 403 if the user is not authorized to access this meeting
    """
    return get_transcription_waiting_time(
        meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid
    )


@router.get("/transcription/wait-time/estimation")
async def get_queue_estimated_waiting_time() -> TranscriptionQueueStatusResponse:
    """
    Get the estimated waiting time for new meetings joining the transcription queue.

    Calculate the estimated time based on the total number of pending meetings and average processing time.
    """
    return TranscriptionQueueStatusResponse(
        estimation_duration_minutes=TranscriptionQueueEstimationService.get_queue_estimated_waiting_time_minutes()
    )
