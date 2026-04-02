from fastapi import APIRouter, Depends, HTTPException

from mcr_gateway.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.lookup_service import lookup_comu_meeting_service

router = APIRouter()


@router.post(
    "/lookup",
    response_model=ComuMeetingLookupResponse,
    tags=["External visio"],
)
async def lookup_meeting(
    meeting_data: ComuMeetingLookup,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> ComuMeetingLookupResponse:
    try:
        return await lookup_comu_meeting_service(
            meeting_data, user_keycloak_uuid=current_user.keycloak_uuid
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
