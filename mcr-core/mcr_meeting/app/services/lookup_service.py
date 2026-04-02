from mcr_meeting.app.client.comu_client import ComuClient
from mcr_meeting.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)


async def lookup_comu_meeting_service(
    meeting_data: ComuMeetingLookup,
) -> ComuMeetingLookupResponse:
    client = ComuClient()
    if meeting_data.secret is not None:
        return await client.lookup_with_secret(
            meeting_data.comu_meeting_id, meeting_data.secret
        )
    if meeting_data.passcode is not None:
        return await client.lookup_with_passcode(
            meeting_data.comu_meeting_id,
            meeting_data.passcode,
        )
    raise ValueError("Either 'secret' or 'passcode' must be provided")
