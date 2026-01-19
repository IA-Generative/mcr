from unittest.mock import patch

import pytest

from mcr_meeting.app.services import s3_service


@pytest.fixture
def s3_settings_mock(monkeypatch):
    class DummySettings:
        S3_BUCKET = "test-bucket"
        S3_TRANSCRIPTION_FOLDER = "transcriptions"
        S3_REPORT_FOLDER = "reports"
        S3_AUDIO_FOLDER = "audio"

    monkeypatch.setattr(s3_service, "s3_settings", DummySettings())
    return DummySettings()


@patch("mcr_meeting.app.services.s3_service.s3_client")
def test_create_multipart_upload_success(mock_s3_client, s3_settings_mock):
    from mcr_meeting.app.schemas.S3_types import MultipartInitRequest

    mock_s3_client.create_multipart_upload.return_value = {
        "UploadId": "1234",
        "Key": "test-key",
    }
    req = MultipartInitRequest(filename="test-key.wav", content_type="audio/wav")
    result = s3_service.create_multipart_upload(123, req)
    assert result["upload_id"] == "1234"
    assert result["key"] == "test-key"
    assert result["bucket"] == s3_settings_mock.S3_BUCKET


@patch("mcr_meeting.app.services.s3_service.s3_client")
def test_create_multipart_upload_failure(mock_s3_client):
    mock_s3_client.create_multipart_upload.side_effect = Exception("fail")
    with pytest.raises(Exception):
        s3_service.create_multipart_upload("test-key", "audio/wav")


@patch("mcr_meeting.app.services.s3_service.s3_external_client")
def test_get_presigned_url_for_upload_part_success(mock_external_client):
    mock_external_client.generate_presigned_url.return_value = "http://presigned-url"
    url = s3_service.get_presigned_url_for_upload_part("test-key", "uploadid", 1)
    assert url == "http://presigned-url"


@patch("mcr_meeting.app.services.s3_service.s3_external_client")
def test_get_presigned_url_for_upload_part_failure(mock_external_client):
    mock_external_client.generate_presigned_url.side_effect = Exception("fail")
    with pytest.raises(Exception):
        s3_service.get_presigned_url_for_upload_part("test-key", "uploadid", 1)


@patch("mcr_meeting.app.services.s3_service.s3_client")
def test_complete_multipart_upload_success(mock_s3_client):
    from mcr_meeting.app.schemas.S3_types import (
        MultipartCompletePart,
        MultipartCompleteRequest,
    )

    mock_s3_client.complete_multipart_upload.return_value = {}
    parts = [
        MultipartCompletePart(part_number=1, etag="etag1"),
        MultipartCompletePart(part_number=2, etag="etag2"),
    ]
    req = MultipartCompleteRequest(
        upload_id="uploadid", object_key="test-key", parts=parts
    )
    s3_service.complete_multipart_upload(req)
    mock_s3_client.complete_multipart_upload.assert_called_once()


@patch("mcr_meeting.app.services.s3_service.s3_client")
def test_complete_multipart_upload_failure(mock_s3_client):
    mock_s3_client.complete_multipart_upload.side_effect = Exception("fail")
    with pytest.raises(Exception):
        s3_service.complete_multipart_upload("test-key", "uploadid", [])


@patch("mcr_meeting.app.services.s3_service.s3_client")
def test_abort_multipart_upload_success(mock_s3_client):
    mock_s3_client.abort_multipart_upload.return_value = {}
    s3_service.abort_multipart_upload("test-key", "uploadid")
    mock_s3_client.abort_multipart_upload.assert_called_once()


@patch("mcr_meeting.app.services.s3_service.s3_client")
def test_abort_multipart_upload_failure(mock_s3_client):
    mock_s3_client.abort_multipart_upload.side_effect = Exception("fail")
    with pytest.raises(Exception):
        s3_service.abort_multipart_upload("test-key", "uploadid")
