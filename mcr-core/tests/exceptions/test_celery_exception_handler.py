import pytest
from fastapi import status

from mcr_meeting.app.exceptions.celery_exception_handler import raise_for_core_status
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException

MEETING_ID = 42


def test_conflict_returns_true_to_short_circuit() -> None:
    # 409 is fully handled (the transition already happened): the caller must
    # stop and must NOT fall through to response.raise_for_status(), which
    # would otherwise re-raise on the 4xx.
    assert raise_for_core_status(status.HTTP_409_CONFLICT, MEETING_ID) is True


@pytest.mark.parametrize(
    "status_code",
    [
        status.HTTP_200_OK,
        status.HTTP_204_NO_CONTENT,
        # other non-2xx are left to the caller's response.raise_for_status().
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ],
)
def test_status_returns_false_to_fall_through(status_code: int) -> None:
    assert raise_for_core_status(status_code, MEETING_ID) is False


def test_not_found_raises_meeting_deleted() -> None:
    with pytest.raises(MeetingDeletedException):
        raise_for_core_status(status.HTTP_404_NOT_FOUND, MEETING_ID)
