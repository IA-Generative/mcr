import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    MeetingStateConflictException,
)
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.use_cases.start_capture_bot import start_capture_bot
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_start_capture_bot_sets_status_and_start_date(
    user_fixture: User, db_session: Session
) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    result = start_capture_bot(
        meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
    )

    # Assert
    assert result.status == MeetingStatus.CAPTURE_IN_PROGRESS
    assert result.start_date is not None
    records = (
        db_session.query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting.id,
            MeetingTransitionRecord.status == MeetingStatus.CAPTURE_IN_PROGRESS,
        )
        .all()
    )
    assert len(records) == 1


def test_start_capture_bot_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        start_capture_bot(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )


def test_start_capture_bot_rejects_illegal_transition(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(MeetingStateConflictException):
        start_capture_bot(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )
