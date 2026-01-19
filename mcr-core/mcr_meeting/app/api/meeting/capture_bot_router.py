from fastapi import (
    APIRouter,
    Depends,
    Header,
    Response,
    status,
)
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    fail_capture_bot,
    start_capture_bot,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Meetings", "Capture Bot"],
)


@router.post("/{meeting_id}/capture/bot/start")
async def start_meeting_capture_bot(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> Response:
    """
    Init meeting capture.

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        HTTP 204 status code if successful
    """
    start_capture_bot(meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{meeting_id}/capture/bot/fail")
async def fail_meeting_capture_bot(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> Response:
    """
    Init meeting capture.

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        HTTP 204 status code if successful
    """
    fail_capture_bot(meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
