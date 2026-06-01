import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    NotFoundException,
)
from mcr_meeting.app.models import Meeting, MeetingStatus, User
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.schemas.meeting_schema import MeetingUpdate
from mcr_meeting.app.use_cases.update_meeting import update_meeting
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def test_update_meeting_patches_provided_fields(
    db_session: Session, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        name="Old name",
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    result = update_meeting(
        meeting_id=meeting.id,
        meeting_update=MeetingUpdate(name="New name"),
        user_keycloak_uuid=user_fixture.keycloak_uuid,
    )

    # Assert
    assert result.name == "New name"
    db_meeting = db_session.get(Meeting, meeting.id)
    assert db_meeting is not None
    assert db_meeting.name == "New name"


def test_update_meeting_leaves_unset_fields_untouched(
    db_session: Session, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(
        owner=user_fixture,
        name="Original",
        status=MeetingStatus.NONE,
        name_platform=MeetingPlatforms.COMU,
    )

    # Act
    update_meeting(
        meeting_id=meeting.id,
        meeting_update=MeetingUpdate(name="Renamed"),
        user_keycloak_uuid=user_fixture.keycloak_uuid,
    )

    # Assert
    db_meeting = db_session.get(Meeting, meeting.id)
    assert db_meeting is not None
    assert db_meeting.status == MeetingStatus.NONE


def test_update_meeting_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(name_platform=MeetingPlatforms.COMU)

    # Act & Assert
    with pytest.raises(ForbiddenAccessException) as exception:
        update_meeting(
            meeting_id=meeting.id,
            meeting_update=MeetingUpdate(name="Hijacked"),
            user_keycloak_uuid=user_fixture.keycloak_uuid,
        )

    assert "Meeting is owned by a different user" in str(exception.value)


def test_update_meeting_raises_when_meeting_does_not_exist(user_fixture: User) -> None:
    # Act & Assert
    with pytest.raises(NotFoundException):
        update_meeting(
            meeting_id=999_999,
            meeting_update=MeetingUpdate(name="Ghost"),
            user_keycloak_uuid=user_fixture.keycloak_uuid,
        )
