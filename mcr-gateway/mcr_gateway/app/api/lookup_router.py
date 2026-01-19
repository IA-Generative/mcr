from fastapi import APIRouter, Depends, HTTPException

from mcr_gateway.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)
from mcr_gateway.app.schemas.user_schema import Role
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.lookup_service import lookup_comu_meeting_service

router = APIRouter()


@router.post(
    "/lookup",
    response_model=ComuMeetingLookupResponse,
    tags=["COMU"],
    dependencies=[Depends(authorize_user(Role.USER.value))],
)
async def lookup_meeting(meeting_data: ComuMeetingLookup) -> ComuMeetingLookupResponse:
    try:
        comu_data = await lookup_comu_meeting_service(meeting_data)
        return comu_data
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Error occurred while looking up the meeting: {e.detail}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
