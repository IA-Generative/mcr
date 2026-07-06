import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription._shared.on_pipeline_failure as opf
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException

MEETING_ID = 123
OWNER = "owner-uuid"


# on_pipeline_failure runs inside the on_failure hook, so it must not let a
# deleted-meeting 404 escape (that would become a Celery internal error).
def test_swallows_meeting_deleted(mocker: MockerFixture) -> None:
    client_cls = mocker.patch.object(opf, "MeetingApiClient")
    client_cls.return_value.mark_transcription_as_failed = mocker.AsyncMock(
        side_effect=MeetingDeletedException()
    )

    opf.on_pipeline_failure(MEETING_ID, OWNER, error_code="diarize")


def test_propagates_unexpected_error(mocker: MockerFixture) -> None:
    client_cls = mocker.patch.object(opf, "MeetingApiClient")
    client_cls.return_value.mark_transcription_as_failed = mocker.AsyncMock(
        side_effect=RuntimeError("core unreachable")
    )

    with pytest.raises(RuntimeError):
        opf.on_pipeline_failure(MEETING_ID, OWNER, error_code="diarize")
