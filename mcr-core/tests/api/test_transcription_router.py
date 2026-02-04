# type: ignore[explicit-any]

from datetime import datetime, timezone
from typing import Callable
from unittest.mock import Mock

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from mcr_meeting.app.models.meeting_model import Meeting, MeetingStatus
from mcr_meeting.app.models.user_model import User

from .conftest import PrefixedTestClient


class TestCreateTranscriptionTask:
    """Test cases for the transcription_task/create endpoint."""

    def test_success(
        self,
        meeting_client: PrefixedTestClient,
        meeting_factory: Callable[..., Meeting],
        mock_celery_producer_app: Mock,
    ) -> None:
        """Test successful transcription task creation."""
        # Arrange
        meeting = meeting_factory(status=MeetingStatus.CAPTURE_DONE)
        # Act
        response = meeting_client.post(f"/{meeting.id}/transcription/init")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_celery_producer_app.send_task.assert_called_once_with(
            "transcription_worker.transcribe", args=[meeting.id]
        )

    @pytest.mark.parametrize(
        "mock_celery_producer_app",
        [Exception("Celery connection failed")],
        indirect=True,
    )
    def test_celery_error(
        self,
        meeting_client: PrefixedTestClient,
        meeting_factory: Callable[..., Meeting],
        mock_celery_producer_app: Mock,
    ) -> None:
        """Test handling of Celery task creation errors."""
        # Arrange
        meeting = meeting_factory(status=MeetingStatus.CAPTURE_DONE)

        # Act
        response = meeting_client.post(f"/{meeting.id}/transcription/init")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "detail" in response_data
        assert "Celery connection failed" in response_data["detail"]
        mock_celery_producer_app.send_task.assert_called_once_with(
            "transcription_worker.transcribe", args=[meeting.id]
        )

    def test_get_meeting_transcription_waiting_time_should_return_200_when_authorized(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        meeting_fixture: Meeting,
        mocker: Mock,
    ) -> None:
        """Test that the endpoint returns 200 with correct data when user is authorized."""
        # Arrange
        meeting_id = meeting_fixture.id
        expected_waiting_time = 24

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes",
            return_value=expected_waiting_time,
        )

        # Act
        response = meeting_client.get(
            f"/{meeting_id}/transcription/wait-time",
            headers={"X-User-Keycloak-Uuid": str(user_fixture.keycloak_uuid)},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "estimation_duration_minutes" in data
        assert data["estimation_duration_minutes"] == expected_waiting_time

    def test_get_meeting_transcription_waiting_time_should_return_404_when_meeting_not_found(
        self, meeting_client: PrefixedTestClient, user_fixture: User
    ) -> None:
        """Test that the endpoint returns 404 when meeting does not exist."""
        # Arrange
        meeting_id = 999

        # Act
        response = meeting_client.get(
            f"/{meeting_id}/transcription/wait-time",
            headers={"X-User-Keycloak-Uuid": str(user_fixture.keycloak_uuid)},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_meeting_transcription_waiting_time_should_return_403_when_user_unauthorized(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        user_2_fixture: User,
        db_session: Session,
    ) -> None:
        """Test that the endpoint returns 403 when user is not authorized for the meeting."""
        # Arrange - Create a meeting that belongs to user_fixture
        meeting = Meeting(
            user_id=user_fixture.id,
            name="User 1 Meeting",
            status=MeetingStatus.TRANSCRIPTION_PENDING,
            name_platform="COMU",
            creation_date=datetime.now(timezone.utc),
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)

        # user_2 tries to access user_fixture's meeting
        meeting_id = meeting.id

        # Act
        response = meeting_client.get(
            f"/{meeting_id}/transcription/wait-time",
            headers={"X-User-Keycloak-Uuid": str(user_2_fixture.keycloak_uuid)},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        detail_lower = response.json()["detail"].lower()
        assert "unauthorized" in detail_lower or "different user" in detail_lower

    def test_get_meeting_transcription_waiting_time_should_return_zero_for_first_meeting(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        meeting_fixture: Meeting,
        mocker: Mock,
    ) -> None:
        """Test that waiting time is 0 when there are no pending meetings before."""
        # Arrange
        meeting_id = meeting_fixture.id

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes",
            return_value=0,
        )

        # Act
        response = meeting_client.get(
            f"/{meeting_id}/transcription/wait-time",
            headers={"X-User-Keycloak-Uuid": str(user_fixture.keycloak_uuid)},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estimation_duration_minutes"] == 0

    def test_get_meeting_transcription_waiting_time_should_return_correct_estimation_for_multiple_meetings(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        meeting_fixture: Meeting,
        mocker: Mock,
    ) -> None:
        """Test correct estimation with multiple pending meetings."""
        # Arrange
        meeting_id = meeting_fixture.id
        expected_waiting_time = 36

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes",
            return_value=expected_waiting_time,
        )

        # Act
        response = meeting_client.get(
            f"/{meeting_id}/transcription/wait-time",
            headers={"X-User-Keycloak-Uuid": str(user_fixture.keycloak_uuid)},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estimation_duration_minutes"] == expected_waiting_time

    def test_get_meeting_transcription_waiting_time_should_validate_response_schema(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        meeting_fixture: Meeting,
        mocker: Mock,
    ) -> None:
        """Test that the response follows the correct schema."""
        # Arrange
        meeting_id = meeting_fixture.id

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes",
            return_value=12,
        )

        # Act
        response = meeting_client.get(
            f"/{meeting_id}/transcription/wait-time",
            headers={"X-User-Keycloak-Uuid": str(user_fixture.keycloak_uuid)},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "estimation_duration_minutes" in data
        assert isinstance(data["estimation_duration_minutes"], int)
        assert data["estimation_duration_minutes"] >= 0

    def test_get_meeting_transcription_waiting_time_should_require_authentication_header(
        self, meeting_client: PrefixedTestClient, meeting_fixture: Meeting
    ) -> None:
        """Test that the endpoint requires authentication header."""
        # Arrange
        meeting_id = meeting_fixture.id

        # Act - No authentication header
        response = meeting_client.get(f"/{meeting_id}/transcription/wait-time")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
