import httpx
import pytest
from fastapi import status

from mcr_meeting.app.client.meeting_client import _raise_for_core_status
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException

MEETING_ID = 42


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=httpx.Request("POST", "http://test"))


def test_conflict_is_swallowed() -> None:
    # 409 means the transition already happened: handled, no raise.
    _raise_for_core_status(_response(status.HTTP_409_CONFLICT), MEETING_ID)


@pytest.mark.parametrize(
    "status_code",
    [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT],
)
def test_success_does_not_raise(status_code: int) -> None:
    _raise_for_core_status(_response(status_code), MEETING_ID)


def test_not_found_raises_meeting_deleted() -> None:
    with pytest.raises(MeetingDeletedException):
        _raise_for_core_status(_response(status.HTTP_404_NOT_FOUND), MEETING_ID)


def test_server_error_raises_http_status_error() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        _raise_for_core_status(
            _response(status.HTTP_500_INTERNAL_SERVER_ERROR), MEETING_ID
        )
