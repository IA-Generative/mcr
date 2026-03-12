from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi.responses import StreamingResponse

from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.meeting_audio_service import (
    MAX_DELAY_TO_GET_AUDIO,
    get_meeting_audio_service,
    stream_audio_chunks,
)
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    user = UserFactory.create()
    return user


class TestMeetingAudioService:
    """Test suite for the meeting_audio_service file."""

    @patch("mcr_meeting.app.services.meeting_audio_service.get_file_from_s3")
    @patch(
        "mcr_meeting.app.services.meeting_audio_service.get_extension_from_object_list"
    )
    @patch(
        "mcr_meeting.app.services.meeting_audio_service.get_objects_list_from_prefix"
    )
    def test_get_meeting_audio_service_success(
        self,
        mock_get_objects: Mock,
        mock_get_extension: Mock,
        mock_get_file: Mock,
        user_fixture: User,
    ):
        # Arrange
        meeting_data = MeetingFactory.create(owner=user_fixture)
        s3_obj = S3Object(
            bucket_name="test-bucket",
            object_name=f"audio/{meeting_data.id}/1234.weba",
            last_modified=None,
        )
        mock_get_objects.return_value = iter([s3_obj])
        mock_get_extension.return_value = (iter([s3_obj]), "weba")
        mock_get_file.return_value = BytesIO(b"fake_audio")

        # Act
        result = get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert
        assert isinstance(result, StreamingResponse)
        assert result.media_type == "audio/webm"

    def test_get_meeting_audio_service_fails_if_requester_isnt_owner(
        self, user_fixture: User
    ):
        # Arrange
        meeting_data = MeetingFactory.create()

        # Act
        with pytest.raises(ForbiddenAccessException) as exception:
            get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert
        assert "Meeting is owned by a different user" in str(exception.value)

    def test_get_meeting_audio_service_fails_if_creation_date_over_a_week(
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

    @patch("mcr_meeting.app.services.meeting_audio_service.get_file_from_s3")
    @patch(
        "mcr_meeting.app.services.meeting_audio_service.get_extension_from_object_list"
    )
    @patch(
        "mcr_meeting.app.services.meeting_audio_service.get_objects_list_from_prefix"
    )
    def test_get_meeting_audio_service_succeeds_if_creation_date_under_a_week(
        self,
        mock_get_objects: Mock,
        mock_get_extension: Mock,
        mock_get_file: Mock,
        user_fixture: User,
    ):
        # Arrange
        meeting_data = MeetingFactory.create(owner=user_fixture)
        meeting_data.creation_date = datetime.now(timezone.utc) - timedelta(
            days=6, hours=23, minutes=55
        )
        s3_obj = S3Object(
            bucket_name="test-bucket",
            object_name=f"audio/{meeting_data.id}/1234.weba",
            last_modified=None,
        )
        mock_get_objects.return_value = iter([s3_obj])
        mock_get_extension.return_value = (iter([s3_obj]), "weba")
        mock_get_file.return_value = BytesIO(b"fake_audio")

        # Act
        result = get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

        # Assert
        assert isinstance(result, StreamingResponse)
        assert result.media_type == "audio/webm"

    @patch(
        "mcr_meeting.app.services.meeting_audio_service.get_objects_list_from_prefix"
    )
    def test_get_meeting_audio_service_raises_when_no_audio_files(
        self, mock_get_objects: Mock, user_fixture: User
    ):
        # Arrange
        meeting_data = MeetingFactory.create(owner=user_fixture)
        mock_get_objects.return_value = iter([])

        # Act & Assert
        with pytest.raises(ValueError, match="No audio files found"):
            get_meeting_audio_service(meeting_data.id, user_fixture.keycloak_uuid)

    # --- stream_audio_chunks ---

    @patch("mcr_meeting.app.services.meeting_audio_service.get_file_from_s3")
    def test_stream_audio_chunks_yields_bytes_in_order(self, mock_get_file: Mock):
        # Arrange
        mock_get_file.side_effect = [
            BytesIO(b"chunk_1"),
            BytesIO(b"chunk_2"),
            BytesIO(b"chunk_3"),
        ]
        s3_objects = [
            S3Object(
                bucket_name="b",
                object_name=f"audio/1/{i}.weba",
                last_modified=None,
            )
            for i in range(3)
        ]

        # Act
        result = list(stream_audio_chunks(iter(s3_objects)))

        # Assert
        assert result == [b"chunk_1", b"chunk_2", b"chunk_3"]
        assert mock_get_file.call_count == 3

    def test_stream_audio_chunks_with_empty_iterator(self):
        # Act
        result = list(stream_audio_chunks(iter([])))

        # Assert
        assert result == []
