from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Response,
    status,
)
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.orchestrators.meeting_orchestrator import (
    create_meeting as create_meeting_orchestrator,
)
from mcr_meeting.app.orchestrators.meeting_orchestrator import (
    create_meeting_with_presigned_url as create_meeting_with_presigned_url_orchestrator,
)
from mcr_meeting.app.orchestrators.meeting_orchestrator import (
    generate_presigned_audio_upload_url as generate_presigned_audio_upload_url_orchestrator,
)
from mcr_meeting.app.orchestrators.meeting_orchestrator import (
    get_meeting as get_meeting_orchestrator,
)
from mcr_meeting.app.orchestrators.meeting_orchestrator import (
    get_meetings as get_meetings_orchestrator,
)
from mcr_meeting.app.orchestrators.meeting_orchestrator import (
    update_meeting as update_meeting_orchestrator,
)
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    delete as delete_meeting_orchestrator,
)
from mcr_meeting.app.schemas.meeting_schema import (
    MeetingCreate,
    MeetingResponse,
    MeetingUpdate,
    MeetingWithPresignedUrl,
)
from mcr_meeting.app.schemas.S3_types import (
    PresignedAudioFileRequest,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Meetings"],
)


@router.post("/")
def create_meeting(
    meeting_data: MeetingCreate,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> MeetingResponse:
    """
    Create a new meeting.

    Args:
        meeting_data (MeetingCreate): The meeting data to create.

    Returns:
        Meeting: The created meeting object.
    """
    meeting = create_meeting_orchestrator(
        meeting_data=meeting_data,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )
    return MeetingResponse.model_validate(meeting)


@router.post("/create_and_generate_presigned_url", tags=["Audio"])
async def create_meeting_with_file(
    meeting_data: MeetingCreate,
    presigned_request: PresignedAudioFileRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> MeetingWithPresignedUrl:
    """
    Create a new meeting and return a presigned url to upload an audio file.

    Args:
        meeting_data (MeetingCreate): The meeting data to create.

    Returns:
        Meeting: The created meeting object.
        str: Presigned URL for uploading an audio file.
    """
    return await create_meeting_with_presigned_url_orchestrator(
        meeting_data=meeting_data,
        presigned_request=presigned_request,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )


@router.get("/")
def get_meetings(
    x_user_keycloak_uuid: UUID4 = Header(),
    search: str = Query(None, description="Terme de recherche optionnel"),
    page: int = Query(1, description="Numéro de page"),
    page_size: int = Query(10, description="Nombre d'éléments par page"),
) -> List[MeetingResponse]:
    """
    Route pour récupérer une liste de réunions filtrées.

    Args:
        search (str): Terme de recherche optionnel.
        page (int): Numéro de page.
        page_size (int): Nombre d'éléments par page.

    Returns:
        List[Meeting]: Liste des réunions correspondant aux critères.
    """
    page = max(1, page)
    page_size = page_size if page_size > 0 else 1
    meetings = get_meetings_orchestrator(
        search=search,
        page=page,
        page_size=page_size,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )
    return [MeetingResponse.model_validate(m) for m in meetings]


@router.get("/{meeting_id}")
def get_meeting(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> MeetingResponse:
    """Retrieve a meeting by ID.
    Returns:
        Meeting: The meeting with the specified ID.
    """
    meeting = get_meeting_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )
    return MeetingResponse.model_validate(meeting)


@router.put("/{meeting_id}")
def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> MeetingResponse:
    """
    Update an existing meeting by ID.

    Args:
        meeting_id (int): The ID of the meeting to update.
        meeting_update (MeetingUpdate): The new data for the meeting.

    Returns:
        Meeting: The updated meeting object.
    """
    meeting = update_meeting_orchestrator(
        meeting_id=meeting_id,
        meeting_update=meeting_update,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )
    return MeetingResponse.model_validate(meeting)


@router.delete("/{meeting_id}")
def delete_meeting(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> Response:
    """
    Delete a meeting by ID.

    Args:
        meeting_id (int): The ID of the meeting to delete.

    Returns:
        HTTP 204 status code if successful
    """

    delete_meeting_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{meeting_id}/presigned_url/generate",
    tags=["Audio"],
)
async def generate_presigned_url(
    meeting_id: int,
    presigned_request: PresignedAudioFileRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> str:
    return await generate_presigned_audio_upload_url_orchestrator(
        meeting_id=meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        presigned_request=presigned_request,
    )
