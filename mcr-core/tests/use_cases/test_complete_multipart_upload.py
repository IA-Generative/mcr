from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.S3_types import (
    MultipartCompletePart,
    MultipartCompleteRequest,
)
from mcr_meeting.app.use_cases.complete_multipart_upload import (
    complete_multipart_upload,
)
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def _complete_request(meeting_id: int) -> MultipartCompleteRequest:
    return MultipartCompleteRequest(
        upload_id="1",
        object_key=f"audio/{meeting_id}/audio.mp3",
        parts=[MultipartCompletePart(part_number=1, etag="etag1")],
    )


@patch(
    "mcr_meeting.app.use_cases.complete_multipart_upload."
    "complete_multipart_upload_in_s3"
)
def test_complete_multipart_upload_success(
    mock_complete: Mock, user_fixture: User
) -> None:
    # Arrange
    meeting = MeetingFactory.create(owner=user_fixture)
    complete_request = _complete_request(meeting.id)

    # Act
    complete_multipart_upload(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_fixture.keycloak_uuid,
        complete_request=complete_request,
    )

    # Assert
    mock_complete.assert_called_once_with(meeting.id, complete_request)


def test_complete_multipart_upload_fails_if_requester_isnt_owner(
    user_fixture: User,
) -> None:
    # Arrange
    meeting = MeetingFactory.create()

    # Act & Assert
    with pytest.raises(ForbiddenAccessException):
        complete_multipart_upload(
            meeting_id=meeting.id,
            user_keycloak_uuid=user_fixture.keycloak_uuid,
            complete_request=_complete_request(meeting.id),
        )
