import pytest

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    NotFoundException,
)
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.use_cases.delete_meeting import delete_meeting
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_delete_meeting_sets_status_deleted(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    delete_meeting(meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid)

    # Assert
    assert meeting.status == MeetingStatus.DELETED
    # DELETED meetings are filtered out by the repository
    with pytest.raises(NotFoundException):
        get_meeting_by_id(meeting.id)


def test_delete_meeting_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(name_platform=MeetingPlatforms.COMU)

    # Act & Assert
    with pytest.raises(ForbiddenAccessException) as exception:
        delete_meeting(
            meeting_id=meeting.id, user_keycloak_uuid=user_fixture.keycloak_uuid
        )

    assert "Meeting is owned by a different user" in str(exception.value)
