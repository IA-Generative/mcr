from mcr_meeting.app.infrastructure.comu import lookup_meeting
from mcr_meeting.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)


async def lookup_comu_meeting(
    meeting_data: ComuMeetingLookup,
) -> ComuMeetingLookupResponse:
    return await lookup_meeting(meeting_data)
