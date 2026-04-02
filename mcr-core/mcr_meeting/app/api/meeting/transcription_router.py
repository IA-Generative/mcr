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
from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    InvalidFileError,
    NotFoundException,
)
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    fail_transcription,
    init_transcription,
    start_transcription,
)
from mcr_meeting.app.orchestrators.transcription_orchestrator import (
    finalize_transcription,
    get_or_create_transcription_docx,
    get_transcription_waiting_time,
    upload_transcription_docx,
)
from mcr_meeting.app.orchestrators.transcription_orchestrator import (
    update_transcription_vote as update_transcription_vote_orchestrator,
)
from mcr_meeting.app.schemas.deliverable_schema import (
    VoteRequest,
)
from mcr_meeting.app.schemas.transcription_queue_schema import (
    TranscriptionQueueStatusResponse,
)
from mcr_meeting.app.schemas.transcription_schema import (
    SpeakerTranscription,
)
from mcr_meeting.app.services.token_exchange_service import ensure_offline_token
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE, validate_docx_upload
from mcr_meeting.app.utils.filename_header import create_safe_filename_header

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

    headers = create_safe_filename_header(result.filename)

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
    try:
        await validate_docx_upload(file)
    except InvalidFileError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Please upload a DOCX file.",
        )

    upload_transcription_docx(
        meeting_id=meeting_id, file=file, user_keycloak_uuid=x_user_keycloak_uuid
    )


@router.post("/{meeting_id}/transcription/init", status_code=status.HTTP_204_NO_CONTENT)
async def init_transcription_task(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 | None = Header(default=None),
    x_user_access_token: str | None = Header(default=None),
) -> None:
    init_transcription(meeting_id=meeting_id)
    if x_user_keycloak_uuid is not None:
        ensure_offline_token(str(x_user_keycloak_uuid), x_user_access_token)


@router.post(
    "/{meeting_id}/transcription/start", status_code=status.HTTP_204_NO_CONTENT
)
async def start_transcription_task(meeting_id: int) -> None:
    start_transcription(meeting_id=meeting_id)


@router.post("/{meeting_id}/transcription/fail", status_code=status.HTTP_204_NO_CONTENT)
async def fail_transcription_task(meeting_id: int) -> None:
    fail_transcription(meeting_id=meeting_id)


@router.post(
    "/{meeting_id}/transcription/success", status_code=status.HTTP_204_NO_CONTENT
)
async def success_transcription_task(
    meeting_id: int, payload: list[SpeakerTranscription]
) -> None:
    finalize_transcription(meeting_id=meeting_id, transcriptions=payload)


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
        estimation_duration_minutes=TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
    )


@router.post("/{meeting_id}/transcription/vote", status_code=status.HTTP_204_NO_CONTENT)
def update_transcription_vote(
    meeting_id: int, current_user_keycloak_uuid: UUID4, vote_request: VoteRequest
) -> None:
    """
    Endpoint to update the vote of a transcription deliverable.


    Raises:
        HTTPException: 404 if the transcription does not exist
        HTTPException: 403 if the user is not authorized to access this meeting
        HTTPException: 409 if a vote already exists for this transcription deliverable
    """
    try:
        update_transcription_vote_orchestrator(
            meeting_id=meeting_id,
            current_user_keycloak_uuid=current_user_keycloak_uuid,
            vote_request=vote_request,
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription deliverable not found for meeting id {meeting_id}",
        )
    except ForbiddenAccessException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User with UUID {current_user_keycloak_uuid} is not authorized to access meeting id {meeting_id}",
        )
    except InvalidFileError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
