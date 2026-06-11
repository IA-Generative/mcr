import pytest

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    MeetingStateConflictException,
)
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.use_cases.init_capture import init_capture
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_init_capture_sets_status_to_capture_pending(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.NONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    result = init_capture(
        meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
    )

    # Assert
    assert result.status == MeetingStatus.CAPTURE_PENDING


def test_init_capture_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        status=MeetingStatus.NONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        init_capture(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )


def test_init_capture_rejects_illegal_transition(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(MeetingStateConflictException):
        init_capture(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )
