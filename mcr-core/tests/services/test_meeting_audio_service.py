from datetime import datetime, timedelta, timezone

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.services.meeting_audio_service import (
    MAX_DELAY_TO_GET_AUDIO,
    get_meeting_audio_service,
)
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    user = UserFactory.create()
    return user


class TestMeetingAudioService:
    """Test suite for the meeting_audio_service file."""

    def test_get_meeting_audio_service_success(self, user_fixture: User):
        # Arrange
        meeting_data = MeetingFactory.create(owner=user_fixture)

        # Act
        get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert : test passes if no error is raised

    def test_get_meeting_audio_service_success_fails_if_requester_isnt_owner(
        self, user_fixture: User
    ):
        # Arrange
        meeting_data = MeetingFactory.create()

        # Act
        with pytest.raises(ForbiddenAccessException) as exception:
            get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert
        assert "Meeting is owned by a different user" in str(exception.value)

    def test_get_meeting_audio_service_success_fails_if_creation_date_over_a_week(
        self, user_fixture: User
    ):
        # Arrange
        meeting_data = MeetingFactory.create(owner=user_fixture)
        meeting_data.creation_date = datetime.now(timezone.utc) - timedelta(
            days=7, minutes=5
        )

        # Act
        with pytest.raises(ForbiddenAccessException) as exception:
            get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert
        assert (
            f"Meeting must have been created in the last {MAX_DELAY_TO_GET_AUDIO} days to access its audio"
            in str(exception.value)
        )

    def test_get_meeting_audio_service_success_succeeds_if_creation_date_under_a_week(
        self, user_fixture: User
    ):
        # Arrange
        meeting_data = MeetingFactory.create(owner=user_fixture)
        meeting_data.creation_date = datetime.now(timezone.utc) - timedelta(
            days=6, hours=23, minutes=55
        )

        # Act
        get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert : test passes if no error is raised
