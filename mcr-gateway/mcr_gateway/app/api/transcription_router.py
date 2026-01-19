from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.transcription_service import (
    get_transcription_waiting_time_service,
)

router = APIRouter()


@router.get("/meetings/{meeting_id}/transcription/wait-time")
async def get_meeting_transcription_waiting_time(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Dict[str, Any]:
    """
    Get the estimated waiting time for the transcription of a given meeting.

    Args:
        meeting_id: The ID of the meeting for which to calculate the waiting time
        current_user: The authenticated user

    Returns:
        TranscriptionQueueStatusResponse: Contains the estimated waiting time in minutes

    Raises:
        HTTPException: 404 if the meeting does not exist
        HTTPException: 403 if the user is not authorized to access this meeting
    """
    try:
        result = await get_transcription_waiting_time_service(
            meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
        )
        return result
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Meeting not found")
        elif e.response.status_code == 403:
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Error getting transcription waiting time: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
