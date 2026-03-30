import httpx
from fastapi import APIRouter, HTTPException

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.orchestrators.lookup_orchestrator import lookup_comu_meeting
from mcr_meeting.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)

api_settings = ApiSettings()

router = APIRouter(
    prefix=api_settings.LOOKUP_API_PREFIX,
    tags=["External visio"],
)


@router.post(
    "/",
    response_model=ComuMeetingLookupResponse,
)
async def lookup_meeting(
    meeting_data: ComuMeetingLookup,
) -> ComuMeetingLookupResponse:
    try:
        return await lookup_comu_meeting(meeting_data)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
