# type: ignore[explicit-any]

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import status

from mcr_meeting.app.models.meeting_model import Meeting, MeetingStatus
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
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
            link_error=mock_celery_producer_app.signature.return_value,
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
            link_error=mock_celery_producer_app.signature.return_value,
        )


@pytest.fixture
def mock_complete_transcription(monkeypatch: Any) -> MagicMock:
    uc = MagicMock()
    monkeypatch.setattr(
        "mcr_meeting.app.api.meeting.transcription_router.complete_transcription",
        uc,
    )
    return uc


class TestSuccessTranscriptionTask:
    """Lock the /transcription/success body contract: optional payload.

    The legacy monolithic pipeline still posts the transcription payload; the
    split pipeline posts the status alone and core reads the transcript from
    full_transcript.json in S3. The payload branch dies with the legacy shim.
    """

    def test_with_payload_forwards_it(
        self,
        meeting_client: PrefixedTestClient,
        mock_complete_transcription: MagicMock,
    ) -> None:
        payload = [
            {
                "meeting_id": 123,
                "speaker": "LOCUTEUR_00",
                "transcription_index": 0,
                "transcription": "Bonjour",
                "start": 0.0,
                "end": 1.0,
                "version": 0,
            }
        ]

        response = meeting_client.post("/123/transcription/success", json=payload)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_complete_transcription.assert_called_once_with(
            meeting_id=123,
            transcriptions=[SpeakerTranscription.model_validate(payload[0])],
        )

    def test_without_body_forwards_none(
        self,
        meeting_client: PrefixedTestClient,
        mock_complete_transcription: MagicMock,
    ) -> None:
        response = meeting_client.post("/123/transcription/success")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_complete_transcription.assert_called_once_with(
            meeting_id=123, transcriptions=None
        )
