from unittest.mock import Mock

from fastapi import status
from pydantic import UUID4

from mcr_meeting.app.models import Meeting, User
from mcr_meeting.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartCompletePart,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartSignPartRequest,
)
from mcr_meeting.app.services.s3_service import get_audio_object_prefix

from .conftest import PrefixedTestClient


def test_init_multipart_upload(
    mock_minio: Mock,
    meeting_client: PrefixedTestClient,
    user_fixture: User,
    meeting_fixture: Meeting,
) -> None:
    filename = "audio.mp3"
    mock_minio.create_multipart_upload.return_value = {
        "Key": filename,
        "UploadId": "1",
    }

    # Arrange
    multipart_init_request = MultipartInitRequest(
        filename=filename,
    )
    payload = multipart_init_request.model_dump(mode="json")

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.post(
        f"/{meeting_fixture.id}/multipart/init", json=payload, headers=headers
    )

    # Assert
    json_data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert json_data["upload_id"] is not None
    assert json_data["object_key"] is not None


def test_sign_multipart_part(
    mock_minio: Mock,
    meeting_client: PrefixedTestClient,
    user_fixture: User,
    meeting_fixture: Meeting,
) -> None:
    mock_minio.get_presigned_url_for_upload_part.return_value = "url"

    # Arrange
    multipart_sign_part_request = MultipartSignPartRequest(
        upload_id="1",
        object_key=get_audio_object_prefix(meeting_fixture.id),
        part_number=1,
    )
    payload = multipart_sign_part_request.model_dump(mode="json")

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.post(
        f"/{meeting_fixture.id}/multipart/sign", json=payload, headers=headers
    )

    # Assert
    json_data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert json_data["url"] is not None


def test_complete_multipart(
    mock_minio: Mock,
    meeting_client: PrefixedTestClient,
    user_fixture: User,
    meeting_fixture: Meeting,
) -> None:
    mock_minio.complete_multipart_upload.return_value = None

    # Arrange
    multipart_complete_part_1 = MultipartCompletePart(part_number=1, etag="")
    multipart_complete_part_2 = MultipartCompletePart(part_number=2, etag="")
    multipart_complete_request = MultipartCompleteRequest(
        upload_id="1",
        object_key=get_audio_object_prefix(meeting_fixture.id),
        parts=[multipart_complete_part_1, multipart_complete_part_2],
    )
    payload = multipart_complete_request.model_dump(mode="json")

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.post(
        f"/{meeting_fixture.id}/multipart/complete", json=payload, headers=headers
    )

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_abort_multipart(
    mock_minio: Mock,
    meeting_client: PrefixedTestClient,
    user_fixture: User,
    meeting_fixture: Meeting,
) -> None:
    mock_minio.abort_multipart_upload.return_value = None

    # Arrange
    multipart_abort_request = MultipartAbortRequest(
        upload_id="1",
        object_key=get_audio_object_prefix(meeting_fixture.id),
    )
    payload = multipart_abort_request.model_dump(mode="json")

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.post(
        f"/{meeting_fixture.id}/multipart/abort", json=payload, headers=headers
    )

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT


def get_user_auth_header(user_keycloak_uuid: UUID4) -> dict[str, str]:
    return {"X-User-keycloak-uuid": str(user_keycloak_uuid)}
