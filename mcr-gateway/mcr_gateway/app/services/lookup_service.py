import httpx
from fastapi import HTTPException
from loguru import logger

from mcr_gateway.app.configs.config import settings

from ..schemas.lookup_schema import ComuMeetingLookup, ComuMeetingLookupResponse


async def lookup_comu_meeting_service(
    comu_meeting_data: ComuMeetingLookup,
) -> ComuMeetingLookupResponse:
    """
    Service to lookup a comu meeting and gather metadata about it.

    Args:
        comu_meeting_data (UserCreate): The data required to call the API.

    Returns:
        ComuMeetingLookupResponse: The gathered metadata about the meeting.

    Raises:
        https.HTTPStatusError: If the API returns an error status code.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "numericId": comu_meeting_data.comu_meeting_id,
                "secret": comu_meeting_data.secret,
            }
            response = await client.post(
                settings.COMU_LOOKUP_URL,
                json=payload,
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
