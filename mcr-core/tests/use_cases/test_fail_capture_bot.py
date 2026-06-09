import pytest

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    MeetingStateConflictException,
)
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.use_cases.fail_capture_bot import fail_capture_bot
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_fail_capture_bot_sets_status_connection_failed(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    result = fail_capture_bot(
        meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
    )

    # Assert
    assert result.status == MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED


def test_fail_capture_bot_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_BOT_IS_CONNECTING,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        fail_capture_bot(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )


def test_fail_capture_bot_rejects_illegal_transition(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(MeetingStateConflictException):
        fail_capture_bot(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )
