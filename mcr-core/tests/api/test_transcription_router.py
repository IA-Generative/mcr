# type: ignore[explicit-any]

from collections.abc import Callable
from unittest.mock import Mock

import pytest
from fastapi import status

from mcr_meeting.app.models.meeting_model import Meeting, MeetingStatus
from tests.api.conftest import PrefixedTestClient


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
            "transcription_worker.transcribe",
            args=[meeting.id, str(meeting.owner.keycloak_uuid)],
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
        assert (
            f"Failed to enqueue transcription task for meeting {meeting.id}"
            in response_data["detail"]
        )
        mock_celery_producer_app.send_task.assert_called_once_with(
            "transcription_worker.transcribe",
            args=[meeting.id, str(meeting.owner.keycloak_uuid)],
        )
