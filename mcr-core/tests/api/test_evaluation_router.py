# type: ignore[explicit-any]

import zipfile
from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from tests.api.conftest import PrefixedTestClient


def _build_zip(names: list[str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"content")
    return buffer.getvalue()


def _valid_zip() -> bytes:
    return _build_zip(["raw_audios/audio1.mp3", "reference_transcripts/audio1.json"])


class TestEvaluateFromZip:
    def test_success(
        self,
        transcription_client: PrefixedTestClient,
        mock_celery_producer_app: Mock,
    ) -> None:
        response = transcription_client.post(
            "/evaluation-from-zip",
            files={"file": ("dataset.zip", _valid_zip(), "application/zip")},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_celery_producer_app.send_task.assert_called_once()
        args, kwargs = mock_celery_producer_app.send_task.call_args
        assert args[0] == MCRTranscriptionTasks.EVALUATE

    def test_non_zip_filename_returns_415(
        self,
        transcription_client: PrefixedTestClient,
        mock_celery_producer_app: Mock,
    ) -> None:
        response = transcription_client.post(
            "/evaluation-from-zip",
            files={"file": ("dataset.tar", _valid_zip(), "application/x-tar")},
        )

        assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        mock_celery_producer_app.send_task.assert_not_called()

    def test_invalid_structure_returns_400(
        self,
        transcription_client: PrefixedTestClient,
        mock_celery_producer_app: Mock,
    ) -> None:
        invalid_zip = _build_zip(["raw_audios/audio1.mp3"])

        response = transcription_client.post(
            "/evaluation-from-zip",
            files={"file": ("dataset.zip", invalid_zip, "application/zip")},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_celery_producer_app.send_task.assert_not_called()

    @pytest.mark.parametrize(
        "mock_celery_producer_app",
        [Exception("Celery connection failed")],
        indirect=True,
    )
    def test_celery_error_returns_500(
        self,
        transcription_client: PrefixedTestClient,
        mock_celery_producer_app: Mock,
    ) -> None:
        transcription_client.client = TestClient(
            transcription_client.client.app, raise_server_exceptions=False
        )

        response = transcription_client.post(
            "/evaluation-from-zip",
            files={"file": ("dataset.zip", _valid_zip(), "application/zip")},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"detail": "Internal Server Error"}


class TestEvaluateFromS3:
    def test_success(
        self,
        transcription_client: PrefixedTestClient,
        mock_celery_producer_app: Mock,
    ) -> None:
        response = transcription_client.post(
            "/evaluation-from-s3",
            json={"zip_name": "clean_dataset.zip"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_celery_producer_app.send_task.assert_called_once_with(
            MCRTranscriptionTasks.EVALUATE_FROM_S3, args=["clean_dataset.zip"]
        )

    def test_non_zip_name_returns_400(
        self,
        transcription_client: PrefixedTestClient,
        mock_celery_producer_app: Mock,
    ) -> None:
        response = transcription_client.post(
            "/evaluation-from-s3",
            json={"zip_name": "clean_dataset.tar"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_celery_producer_app.send_task.assert_not_called()
