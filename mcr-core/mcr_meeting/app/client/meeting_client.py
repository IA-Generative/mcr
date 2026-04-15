from mcr_meeting.app.client.http_client import HttpClient
from mcr_meeting.app.configs.base import ApiSettings, ServiceSettings
from mcr_meeting.app.schemas.meeting_schema import MeetingResponse


class MeetingApiClient:
    def __init__(self, user_uuid: str):
        self.api_settings = ApiSettings()
        self.service_settings = ServiceSettings()

        self.client = HttpClient(base_url=self._get_base_url(), token=user_uuid)

    def _get_base_url(self) -> str:
        return f"{self.service_settings.CORE_SERVICE_BASE_URL}{self.api_settings.MEETING_API_PREFIX}"

    async def get_meeting(self, meeting_id: int) -> MeetingResponse:
        response = await self.client.get(f"/{meeting_id}")
        return MeetingResponse.model_validate(response.json())

    async def start_transcription(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/transcription/start")

    async def mark_transcription_as_failed(self, meeting_id: int) -> None:
        await self.client.post(f"/{meeting_id}/transcription/fail")

    async def mark_transcription_as_success(
        self, meeting_id: int, transcription_data: list[dict[str, object]]
    ) -> None:
        await self.client.post(
            f"/{meeting_id}/transcription/success",
            data=transcription_data,
        )
