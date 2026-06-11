import pytest

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    MeetingStateConflictException,
)
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.use_cases.complete_capture import complete_capture
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_complete_capture_sets_status_and_end_date(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    result = complete_capture(
        meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
    )

    # Assert
    assert result.status == MeetingStatus.CAPTURE_DONE
    assert result.end_date is not None


def test_complete_capture_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        complete_capture(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )


def test_complete_capture_rejects_illegal_transition(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act & Assert
    with pytest.raises(MeetingStateConflictException):
        complete_capture(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )
