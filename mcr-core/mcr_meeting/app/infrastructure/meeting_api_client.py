import httpx
from loguru import logger

from mcr_meeting.app.configs.base import ApiSettings, RetrySettings, ServiceSettings
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.exceptions.exceptions import CoreServiceTransientError
from mcr_meeting.app.infrastructure.retry import retry_transient
from mcr_meeting.app.schemas.meeting_schema import MeetingResponse

# Transport-level failures (connect/read/write/pool timeouts, network errors). These
# never carry an HTTP status — status handling stays in _raise_for_core_status. All
# calls here target idempotent core endpoints (a GET, or 409-guarded transitions), so
# replaying the whole transient set is safe.
_CORE_TRANSIENT: tuple[type[Exception], ...] = (httpx.TransportError,)

_retry_settings = RetrySettings()
_with_core_retry = retry_transient(
    on=(CoreServiceTransientError,),
    attempts=_retry_settings.CORE_RETRY_ATTEMPTS,
    initial_delay=_retry_settings.CORE_RETRY_INITIAL_DELAY,
    max_delay=_retry_settings.CORE_RETRY_MAX_DELAY,
)


class MeetingApiClient:
    def __init__(self, user_uuid: str):
        api_settings = ApiSettings()
        service_settings = ServiceSettings()
        self.base_url = (
            f"{service_settings.CORE_SERVICE_BASE_URL}{api_settings.MEETING_API_PREFIX}"
        )
        self.timeout = httpx.Timeout(
            service_settings.CORE_TIMEOUT_SECONDS,
            connect=service_settings.CORE_CONNECT_TIMEOUT_SECONDS,
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-User-Keycloak-UUID": user_uuid,
        }

    @_with_core_retry
    async def get_meeting(self, meeting_id: int) -> MeetingResponse:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout
            ) as client:
                response = await client.get(f"/{meeting_id}", headers=self.headers)
        except _CORE_TRANSIENT as e:
            raise CoreServiceTransientError(
                f"Transient error fetching meeting {meeting_id}"
            ) from e
        response.raise_for_status()
        return MeetingResponse.model_validate(response.json())

    async def start_transcription(self, meeting_id: int) -> None:
        await self._post_transition(meeting_id, "start")

    async def mark_transcription_as_failed(self, meeting_id: int) -> None:
        await self._post_transition(meeting_id, "fail")

    async def mark_transcription_as_success(
        self,
        meeting_id: int,
        transcription_data: list[dict[str, object]] | None = None,
    ) -> None:
        await self._post_transition(meeting_id, "success", data=transcription_data)

    @_with_core_retry
    async def _post_transition(
        self, meeting_id: int, transition: str, data: object | None = None
    ) -> None:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout
            ) as client:
                response = await client.post(
                    f"/{meeting_id}/transcription/{transition}",
                    headers=self.headers,
                    json=data,
                )
        except _CORE_TRANSIENT as e:
            raise CoreServiceTransientError(
                f"Transient error posting '{transition}' transition "
                f"for meeting {meeting_id}"
            ) from e
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
