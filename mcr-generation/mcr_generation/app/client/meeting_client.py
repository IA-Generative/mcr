from mcr_generation.app.client.http_client import HttpClient
from mcr_generation.app.configs.settings import ApiSettings
from mcr_generation.app.schemas.meeting_schema import MeetingResponse


class MeetingApiClient:
    def __init__(self, user_uuid: str | None):
        self.api_settings = ApiSettings()
        self.client = HttpClient(base_url=self._get_base_url(), token=user_uuid)

    def _get_base_url(self) -> str:
        return f"{self.api_settings.MCR_CORE_API_URL}/meetings"

    def get_meeting(self, meeting_id: int) -> MeetingResponse:
        response = self.client.get(f"/{meeting_id}")
        return MeetingResponse.model_validate(response.json())
