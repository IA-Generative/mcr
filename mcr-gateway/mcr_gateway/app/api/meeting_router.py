from typing import Any, Dict, List

import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from loguru import logger

from mcr_gateway.app.schemas.meeting_schema import (
    Meeting,
    MeetingCreate,
    MeetingUpdate,
    MeetingWithPresignedUrl,
)
from mcr_gateway.app.schemas.S3_types import (
    PresignedAudioFileRequest,
)
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.meeting_service import (
    create_meeting_service,
    create_meeting_with_presigned_url_service,
    delete_meeting_service,
    generate_meeting_transcription_document,
    generate_presigned_url_service,
    generate_report,
    get_meeting_service,
    get_meetings_service,
    get_report,
    init_meeting_capture_service,
    start_meeting_transcription_service,
    stop_meeting_capture_service,
    update_meeting_service,
    update_meeting_transcription_service,
)
from mcr_gateway.app.services.transcription_service import (
    get_queue_estimated_waiting_time_service,
)

router = APIRouter()


@router.post(
    "/meetings",
    response_model=Meeting,
    tags=["Meetings"],
)
async def create_meeting(
    meeting_data: MeetingCreate,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Meeting:
    """
    Endpoint to create a new meeting.

    Args:
        meeting_data (MeetingCreate): The meeting details provided by the frontend.

    Returns:
        Meeting: The created meeting object.
    """
    try:
        result = await create_meeting_service(
            meeting_data, user_keycloak_uuid=current_user.keycloak_uuid
        )
        if result is None:
            raise HTTPException(
                status_code=500, detail="Service did not return a valid response"
            )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e


@router.post(
    "/meetings/create_and_generate_presigned_url",
    tags=["Meetings", "Audio"],
)
async def create_meeting_with_file(
    meeting_data: MeetingCreate,
    presigned_request: PresignedAudioFileRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> MeetingWithPresignedUrl:
    """
    Create a new meeting and return a presigned url to upload an audio file.

    Args:
        meeting_data (MeetingCreate): The meeting data to create.

    Returns:
        Meeting: The created meeting object.
        str: Presigned URL for uploading an audio file.
    """
    try:
        result = await create_meeting_with_presigned_url_service(
            meeting_data=meeting_data,
            presigned_request=presigned_request,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e


@router.post(
    "/meetings/{meeting_id}/presigned_url/generate",
    tags=["Meetings", "Audio"],
)
async def generate_presigned_url(
    meeting_id: int,
    presigned_request: PresignedAudioFileRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> str:
    """
    Create a new meeting and return a presigned url to upload an audio file.

    Args:
        meeting_data (MeetingCreate): The meeting data to create.

    Returns:
        Meeting: The created meeting object.
        str: Presigned URL for uploading an audio file.
    """
    try:
        result = await generate_presigned_url_service(
            meeting_id=meeting_id,
            presigned_request=presigned_request,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e


@router.get(
    "/meetings/{meeting_id}",
    response_model=Meeting,
    tags=["Meetings"],
)
async def get_meeting(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Meeting:
    """
    Endpoint to retrieve a meeting by its ID.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The retrieved meeting object.
    """
    try:
        meeting = await get_meeting_service(
            meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
        )
        return meeting
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Meeting not found")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/meetings/{meeting_id}",
    response_model=Meeting,
    tags=["Meetings"],
)
async def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Meeting:
    """
    Endpoint to update an existing meeting.

    Args:
        meeting_id (int): The ID of the meeting to update.
        meeting_update (MeetingUpdate): The updated meeting details provided by the frontend.

    Returns:
        Meeting: The updated meeting object.
    """
    try:
        updated_meeting = await update_meeting_service(
            meeting_id=meeting_id,
            meeting_update=meeting_update,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return updated_meeting
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Meeting not found")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/meetings/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Meetings"],
)
async def delete_meeting(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    """
    API endpoint to delete an existing meeting by its ID

    Args:
        meeting_id (int): The ID of the meeting to delete.

    Returns:
        Response: HTTP 204 status code if successful, no content.
    """
    try:
        await delete_meeting_service(
            meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Meeting not found")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/meetings/{meeting_id}/capture/init",
    tags=["Meetings"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def init_capture(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    """
    Route pour démarrer la transcription d'une réunion en appelant le service mcr-core.
    """
    await init_meeting_capture_service(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.post(
    "/meetings/{meeting_id}/capture/stop",
    tags=["Meetings"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def stop_capture(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    """
    Route pour arrêter la transcription d'une réunion en appelant le service mcr-core.
    """
    # Appelle le service pour arrêter la transcription
    await stop_meeting_capture_service(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.get(
    "/meetings",
    response_model=List[Meeting],
    tags=["Meetings"],
)
async def get_meetings(
    search: str = Query(None, description="Terme de recherche optionnel"),
    page: int = Query(1, description="Numéro de page"),
    page_size: int = Query(10, description="Nombre d'éléments par page"),
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> List[Meeting]:
    """
    Route pour interroger mcr-core et retourner la liste des réunions.
    """
    return await get_meetings_service(
        search=search,
        page=page,
        page_size=page_size,
        user_keycloak_uuid=current_user.keycloak_uuid,
    )


@router.post(
    "/meetings/{meeting_id}/transcription/init",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Meetings"],
)
async def start_meeting_transcription(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    return await start_meeting_transcription_service(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.post(
    "/meetings/{meeting_id}/transcription",
    tags=["Meetings"],
)
async def get_meeting_transcription(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> StreamingResponse:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting
    """
    return await generate_meeting_transcription_document(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.put(
    "/meetings/{meeting_id}/transcription",
    tags=["Meetings"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_meeting_transcription(
    meeting_id: int,
    file: UploadFile,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    """
    Adds the modified transcription with a new version to a given meeting

    Args:
        meeting_id (int): The ID of the meeting.
        file: Transcription DOCX file

    Returns:
        204 if the transcription has been added
    """
    await update_meeting_transcription_service(
        meeting_id=meeting_id, file=file, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.get(
    "/meetings/{meeting_id}/report",
    tags=["Meetings"],
)
async def get_meeting_report(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> StreamingResponse:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting

    """
    return await get_report(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.post(
    "/meetings/{meeting_id}/report",
    tags=["Meetings"],
)
async def generate_meeting_report(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Response:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting

    """
    return await generate_report(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.get("/meetings/transcription/wait-time/estimation")
async def get_queue_estimated_waiting_time(
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Dict[str, Any]:
    """
    Get the current global waiting time for the transcription queue.

    Args:
        current_user: The authenticated user

    Returns:
        Dict[str, Any]: Contains the current global waiting time in minutes

    Raises:
        HTTPException: If the API call fails
    """
    try:
        result = await get_queue_estimated_waiting_time_service(
            user_keycloak_uuid=current_user.keycloak_uuid
        )
        return result
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error getting queue estimated waiting time: {} - {}",
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Error getting queue estimated waiting time: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
