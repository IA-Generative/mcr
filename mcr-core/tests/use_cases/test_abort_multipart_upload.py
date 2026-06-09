from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.S3_types import MultipartAbortRequest
from mcr_meeting.app.use_cases.abort_multipart_upload import abort_multipart_upload
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


@patch("mcr_meeting.app.use_cases.abort_multipart_upload.abort_multipart_upload_in_s3")
def test_abort_multipart_upload_success(mock_abort: Mock, user_fixture: User) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    abort_request = MultipartAbortRequest(
        upload_id="1", object_key=f"audio/{meeting.id}/audio.mp3"
    )

    # Act
    abort_multipart_upload(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        abort_request=abort_request,
    )

    # Assert
    mock_abort.assert_called_once_with(meeting.id, abort_request)


def test_abort_multipart_upload_fails_if_requester_isnt_owner(
    user_fixture: User,
) -> None:
    # Arrange
    meeting = MeetingFactory.create()
    abort_request = MultipartAbortRequest(
        upload_id="1", object_key=f"audio/{meeting.id}/audio.mp3"
    )

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        abort_multipart_upload(
            meeting_id=meeting.id,
            user_keycloak_uuid=user_fixture.keycloak_uuid,
            abort_request=abort_request,
        )
