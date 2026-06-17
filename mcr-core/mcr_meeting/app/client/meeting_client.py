import httpx
from loguru import logger

from mcr_meeting.app.configs.base import ApiSettings, ServiceSettings
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.schemas.meeting_schema import MeetingResponse


class MeetingApiClient:
    def __init__(self, user_uuid: str):
        api_settings = ApiSettings()
        service_settings = ServiceSettings()
        self.base_url = (
            f"{service_settings.CORE_SERVICE_BASE_URL}{api_settings.MEETING_API_PREFIX}"
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-User-Keycloak-UUID": user_uuid,
        }

    async def get_meeting(self, meeting_id: int) -> MeetingResponse:
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get(f"/{meeting_id}", headers=self.headers)
        response.raise_for_status()
        return MeetingResponse.model_validate(response.json())

    async def start_transcription(self, meeting_id: int) -> None:
        await self._post_transition(meeting_id, "start")

    async def mark_transcription_as_failed(self, meeting_id: int) -> None:
        await self._post_transition(meeting_id, "fail")

    async def mark_transcription_as_success(
        self,
        meeting_id: int,
        transcription_data: list[dict[str, object]],
    ) -> None:
        await self._post_transition(meeting_id, "success", data=transcription_data)

    async def _post_transition(
        self, meeting_id: int, transition: str, data: object | None = None
    ) -> None:
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post(
                f"/{meeting_id}/transcription/{transition}",
                headers=self.headers,
                json=data,
            )
        _raise_for_core_status(response, meeting_id)


def _raise_for_core_status(response: httpx.Response, meeting_id: int) -> None:
    if response.status_code == httpx.codes.NOT_FOUND:
        raise MeetingDeletedException()
    if response.status_code == httpx.codes.CONFLICT:
        logger.warning(
            "Core returned 409 for meeting {}: already transitioned; continuing",
            meeting_id,
        )
        return
    response.raise_for_status()
