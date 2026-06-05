from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.meeting_schema import MeetingAudioStream
from mcr_meeting.app.use_cases.get_meeting_audio import (
    MAX_DELAY_TO_GET_AUDIO,
    get_meeting_audio,
)
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


@patch("mcr_meeting.app.use_cases.get_meeting_audio.stream_meeting_audio")
def test_get_meeting_audio_success(
    mock_stream_meeting_audio: object, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    mock_stream_meeting_audio.return_value = (iter([b"fake_audio"]), "audio/webm")

    # Act
    result = get_meeting_audio(meeting.id, user_fixture.keycloak_uuid)

    # Assert
    assert isinstance(result, MeetingAudioStream)
    assert result.media_type == "audio/webm"
    assert list(result.iterator) == [b"fake_audio"]
    mock_stream_meeting_audio.assert_called_once_with(meeting.id)


def test_get_meeting_audio_fails_if_requester_isnt_owner(user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create()

    # Act & Assert
    with pytest.raises(ForbiddenAccessException) as exception:
        get_meeting_audio(meeting.id, user_fixture.keycloak_uuid)

    assert "Meeting is owned by a different user" in str(exception.value)


def test_get_meeting_audio_fails_if_creation_date_over_a_week(
    user_fixture: User,
) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    meeting.creation_date = datetime.now(timezone.utc) - timedelta(days=7, minutes=5)

    # Act & Assert
    with pytest.raises(ForbiddenAccessException) as exception:
        get_meeting_audio(meeting.id, user_fixture.keycloak_uuid)

    assert (
        f"Meeting must have been created in the last {MAX_DELAY_TO_GET_AUDIO} days to access its audio"
        in str(exception.value)
    )


@patch("mcr_meeting.app.use_cases.get_meeting_audio.stream_meeting_audio")
def test_get_meeting_audio_succeeds_if_creation_date_under_a_week(
    mock_stream_meeting_audio: object, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    meeting.creation_date = datetime.now(timezone.utc) - timedelta(
        days=6, hours=23, minutes=55
    )
    mock_stream_meeting_audio.return_value = (iter([b"fake_audio"]), "audio/webm")

    # Act
    result = get_meeting_audio(meeting.id, user_fixture.keycloak_uuid)

    # Assert
    assert isinstance(result, MeetingAudioStream)
    assert result.media_type == "audio/webm"
