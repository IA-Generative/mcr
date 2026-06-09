from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.S3_types import (
    MultipartInitRequest,
    MultipartInitResponse,
)
from mcr_meeting.app.use_cases.init_multipart_upload import init_multipart_upload
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


@patch(
    "mcr_meeting.app.use_cases.init_multipart_upload.initiate_multipart_upload_in_s3"
)
def test_init_multipart_upload_success(mock_initiate: Mock, user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    init_request = MultipartInitRequest(filename="audio.mp3")
    mock_initiate.return_value = MultipartInitResponse(
        upload_id="1", object_key="audio/1/audio.mp3"
    )

    # Act
    result = init_multipart_upload(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        init_request=init_request,
    )

    # Assert
    assert result.upload_id == "1"
    assert result.object_key == "audio/1/audio.mp3"
    mock_initiate.assert_called_once_with(meeting.id, init_request)


def test_init_multipart_upload_fails_if_requester_isnt_owner(
    user_fixture: User,
) -> None:
    # Arrange
    meeting = MeetingFactory.create()

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        init_multipart_upload(
            meeting_id=meeting.id,
            user_keycloak_uuid=user_fixture.keycloak_uuid,
            init_request=MultipartInitRequest(filename="audio.mp3"),
        )
