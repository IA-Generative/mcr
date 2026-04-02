import httpx
from fastapi import HTTPException
from loguru import logger
from pydantic import UUID4

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)
from mcr_gateway.app.services.meeting_service import MCRCoreCustomAuth


async def lookup_comu_meeting_service(
    comu_meeting_data: ComuMeetingLookup,
    user_keycloak_uuid: UUID4,
) -> ComuMeetingLookupResponse:
    try:
        async with httpx.AsyncClient(
            base_url=settings.LOOKUP_SERVICE_URL,
            auth=MCRCoreCustomAuth(user_keycloak_uuid),
        ) as client:
            response = await client.post(
                "", json=comu_meeting_data.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ComuMeetingLookupResponse(**response.json())
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error during meeting lookup: {} - {}",
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error during lookup: {}", str(e))
        raise HTTPException(status_code=500, detail="Unexpected error occurred")
