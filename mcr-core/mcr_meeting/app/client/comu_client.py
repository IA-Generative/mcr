from mcr_meeting.app.client.http_client import HttpClient
from mcr_meeting.app.configs.base import Settings
from mcr_meeting.app.schemas.lookup_schema import (
    ComuMeetingLookupResponse,
)


class ComuClient:
    def __init__(self) -> None:
        settings = Settings()
        self.client = HttpClient(base_url=settings.COMU_LOOKUP_URL)

    async def lookup_with_secret(
        self, comu_meeting_id: str, secret: str
    ) -> ComuMeetingLookupResponse:
        response = await self.client.post(
            "",
            data={"numericId": comu_meeting_id, "secret": secret},
        )
        return ComuMeetingLookupResponse(**response.json())

    async def lookup_with_passcode(
        self, comu_meeting_id: str, passcode: str
    ) -> ComuMeetingLookupResponse:
        response = await self.client.post(
            "",
            data={"numericId": comu_meeting_id, "passcode": passcode},
        )
        return ComuMeetingLookupResponse(**response.json())
