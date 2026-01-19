from mcr_capture_worker.clients.http_client import HttpClient
from mcr_capture_worker.settings.settings import ApiSettings


class MeetingApiClient:
    def __init__(self, user_uuid: str):
        api_settings = ApiSettings()
        self.client = HttpClient(base_url=api_settings.MEETING_PREFIX, token=user_uuid)

    async def init_transcription(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/transcription/init")

    async def start_capture_bot(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/capture/bot/start")

    async def end_capture(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/capture/stop")

    async def fail_capture_bot(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/capture/bot/fail")
