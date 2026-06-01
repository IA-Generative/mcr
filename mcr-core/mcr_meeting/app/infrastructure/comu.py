import httpx

from mcr_meeting.app.configs.base import Settings
from mcr_meeting.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)

settings = Settings()


async def lookup_meeting(meeting_data: ComuMeetingLookup) -> ComuMeetingLookupResponse:
    if meeting_data.secret is not None:
        payload = {
            "numericId": meeting_data.comu_meeting_id,
            "secret": meeting_data.secret,
        }
    elif meeting_data.passcode is not None:
        payload = {
            "numericId": meeting_data.comu_meeting_id,
            "passcode": meeting_data.passcode,
        }
    else:
        raise ValueError("Either 'secret' or 'passcode' must be provided")

    response = await _post(payload)
    return ComuMeetingLookupResponse(**response.json())


async def _post(payload: dict[str, str]) -> httpx.Response:
    async with httpx.AsyncClient(base_url=settings.COMU_LOOKUP_URL) as client:
        response = await client.post(
            "",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        return response
