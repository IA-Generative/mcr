from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import BadRequestException
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.use_cases._shared.report_dispatch import (
    dispatch_requested_report,
)
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


@pytest.fixture
def mock_celery(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mcr_meeting.app.infrastructure.celery.celery_producer_app")


def _transcribed_meeting() -> Meeting:
    return MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
        transcription_filename="transcription.docx",
    )


class TestDispatchRequestedReport:
    """The happy path is covered end-to-end from both callers — see
    test_request_deliverable and test_complete_transcription (drain). What no
    caller can reach, and what only this level can pin, is the type guard."""

    def test_transcription_is_never_dispatched_to_report_generation(
        self,
        mock_celery: MagicMock,
        db_session: Session,
    ) -> None:
        """A transcription comes from the transcription pipeline, never from
        report generation: a REQUESTED transcription row would otherwise sail
        through the state machine and enqueue a bogus generation task."""
        meeting = _transcribed_meeting()
        transcription = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.REQUESTED,
        )

        with pytest.raises(BadRequestException):
            dispatch_requested_report(meeting, transcription)

        mock_celery.send_task.assert_not_called()
        db_session.refresh(transcription)
        assert transcription.status == DeliverableStatus.REQUESTED
