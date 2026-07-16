import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription.run_mark_transcription_failed as uc
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException

MEETING_ID = 123
OWNER = "owner-uuid"


# A deleted meeting (404) is expected on failure marking and must not escape.
def test_swallows_meeting_deleted(mocker: MockerFixture) -> None:
    client_cls = mocker.patch.object(uc, "MeetingApiClient")
    client_cls.return_value.mark_transcription_as_failed = mocker.AsyncMock(
        side_effect=MeetingDeletedException()
    )

    uc.run_mark_transcription_failed(MEETING_ID, OWNER)


def test_propagates_unexpected_error(mocker: MockerFixture) -> None:
    client_cls = mocker.patch.object(uc, "MeetingApiClient")
    client_cls.return_value.mark_transcription_as_failed = mocker.AsyncMock(
        side_effect=RuntimeError("core unreachable")
    )

    with pytest.raises(RuntimeError):
        uc.run_mark_transcription_failed(MEETING_ID, OWNER)
