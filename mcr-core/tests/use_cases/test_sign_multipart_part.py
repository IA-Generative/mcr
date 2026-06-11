from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.S3_types import (
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)
from mcr_meeting.app.use_cases.sign_multipart_part import sign_multipart_part
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


@patch("mcr_meeting.app.use_cases.sign_multipart_part.sign_multipart_part_in_s3")
def test_sign_multipart_part_success(mock_sign: Mock, user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    sign_request = MultipartSignPartRequest(
        upload_id="1", object_key=f"audio/{meeting.id}/audio.mp3", part_number=1
    )
    mock_sign.return_value = MultipartSignPartResponse(url="https://presigned")

    # Act
    result = sign_multipart_part(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        sign_request=sign_request,
    )

    # Assert
    assert result.url == "https://presigned"
    mock_sign.assert_called_once_with(meeting.id, sign_request)


def test_sign_multipart_part_fails_if_requester_isnt_owner(
    user_fixture: User,
) -> None:
    # Arrange
    meeting = MeetingFactory.create()
    sign_request = MultipartSignPartRequest(
        upload_id="1", object_key=f"audio/{meeting.id}/audio.mp3", part_number=1
    )

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        sign_multipart_part(
            meeting_id=meeting.id,
            user_keycloak_uuid=user_fixture.keycloak_uuid,
            sign_request=sign_request,
        )
