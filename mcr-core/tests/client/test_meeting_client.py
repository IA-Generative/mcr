import httpx
import pytest

from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.infrastructure.meeting_api_client import _raise_for_core_status

MEETING_ID = 42


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=httpx.Request("POST", "http://test"))


def test_conflict_is_swallowed() -> None:
    # 409 means the transition already happened: handled, no raise.
    _raise_for_core_status(_response(httpx.codes.CONFLICT), MEETING_ID)


@pytest.mark.parametrize(
    "status_code",
    [httpx.codes.OK, httpx.codes.NO_CONTENT],
)
def test_success_does_not_raise(status_code: int) -> None:
    _raise_for_core_status(_response(status_code), MEETING_ID)


def test_not_found_raises_meeting_deleted() -> None:
    with pytest.raises(MeetingDeletedException):
        _raise_for_core_status(_response(httpx.codes.NOT_FOUND), MEETING_ID)


def test_server_error_raises_http_status_error() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        _raise_for_core_status(_response(httpx.codes.INTERNAL_SERVER_ERROR), MEETING_ID)
