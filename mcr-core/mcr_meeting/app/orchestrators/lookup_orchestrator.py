from mcr_meeting.app.schemas.lookup_schema import (
    ComuMeetingLookup,
    ComuMeetingLookupResponse,
)
from mcr_meeting.app.services.lookup_service import lookup_comu_meeting_service


async def lookup_comu_meeting(
    meeting_data: ComuMeetingLookup,
) -> ComuMeetingLookupResponse:
    return await lookup_comu_meeting_service(meeting_data)
