from mcr_meeting.app.client.http_client import HttpClient
from mcr_meeting.app.configs.base import ApiSettings, ServiceSettings


class MeetingApiClient:
    def __init__(self, user_uuid: str):
        self.api_settings = ApiSettings()
        self.service_settings = ServiceSettings()

        self.client = HttpClient(base_url=self._get_base_url(), token=user_uuid)

    def _get_base_url(self) -> str:
        return f"{self.service_settings.CORE_SERVICE_BASE_URL}{self.api_settings.MEETING_API_PREFIX}"

    async def start_transcription(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/transcription/start")

    async def fail_transcription(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/transcription/fail")

    async def end_transcription(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/transcription/end")
