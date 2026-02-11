import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import status
from pydantic import UUID4

from mcr_meeting.app.models import Meeting, User
from mcr_meeting.app.schemas.meeting_schema import MeetingCreate, MeetingUpdate

from .conftest import PrefixedTestClient


def test_create_meeting(meeting_client: PrefixedTestClient, user_fixture: User) -> None:
    # Arrange
    meeting_create = MeetingCreate(
        name="Super important Meeting",
        creation_date=datetime(2024, 9, 29, 16, 0),
        name_platform="COMU",
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
    )
    expected_result = Meeting(
        name=meeting_create.name,
        creation_date=meeting_create.creation_date,
        name_platform=meeting_create.name_platform,
        url=meeting_create.url,
        id=3,
    )

    payload = meeting_create.model_dump(mode="json")

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.post("/", json=payload, headers=headers)

    # Assert
    json_data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert_json_equal_meeting_model(json_data, expected_result)


def test_get_meetings_success(
    meeting_client: PrefixedTestClient,
    meeting_fixture: Meeting,
    meeting_2_fixture: Meeting,
    user_fixture: User,
) -> None:
    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get("/", headers=headers)

    # Assert
    json_data = response.json()
    assert response.status_code == status.HTTP_200_OK

    assert len(json_data) == 2
    assert isinstance(json_data, list)
    for meeting_json in json_data:
        fixture = (
            meeting_fixture
            if meeting_json["id"] == meeting_fixture.id
            else meeting_2_fixture
        )
        assert_json_equal_meeting_model(meeting_json, fixture)


def test_get_meetings_invalid_user(
    meeting_client: PrefixedTestClient,
) -> None:
    # Arrange
    wrong_uuid = UUID("03bd4344-b7af-45c9-b106-02ea97431bbb")

    # Act
    headers = get_user_auth_header(wrong_uuid)
    response = meeting_client.get("/", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_meetings_search_success(
    meeting_client: PrefixedTestClient, user_fixture: User, meeting_fixture: Meeting
) -> None:
    # Act
    params = {
        "search": meeting_fixture.name,
    }
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get("/", params=params, headers=headers)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    json_data = response.json()

    assert len(json_data) == 1
    assert isinstance(json_data, list)
    assert_json_equal_meeting_model(json_data[0], meeting_fixture)


def test_get_meetings_with_pagination_params(
    meeting_client: PrefixedTestClient,
    meeting_fixture: Meeting,
    meeting_2_fixture: Meeting,
    user_fixture: User,
) -> None:
    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get(
        "/", params={"page": 1, "page_size": 10}, headers=headers
    )

    # Assert
    json_data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert len(json_data) == 2


def test_get_meetings_with_invalid_pagination(
    meeting_client: PrefixedTestClient,
    meeting_fixture: Meeting,
    user_fixture: User,
) -> None:
    # Act — negative values should still return results (clamped in repository)
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get(
        "/", params={"page": -1, "page_size": -1}, headers=headers
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    json_data = response.json()
    assert len(json_data) == 1  # page_size clamped to 1


def test_get_meetings_search_no_result(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Act
    params = {
        "search": "a random name",
    }
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get("/", params=params, headers=headers)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    json_data = response.json()

    assert len(json_data) == 0


def test_get_meeting_by_id_success(
    meeting_client: PrefixedTestClient, meeting_fixture: Meeting, user_fixture: User
) -> None:
    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get(f"/{meeting_fixture.id}", headers=headers)

    # Assert
    json_data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert_json_equal_meeting_model(json_data, meeting_fixture)


def test_get_meeting_by_id_unauthorized(
    meeting_client: PrefixedTestClient, meeting_fixture: Meeting, user_fixture: User
) -> None:
    # Act
    invalid_user_uuid = UUID("03bd4344-b7af-45c9-b106-02ea97431bbb")

    headers = get_user_auth_header(invalid_user_uuid)
    response = meeting_client.get("/1", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_meeting_by_id_not_found(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.get("/999", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_meeting_success(
    meeting_client: PrefixedTestClient, meeting_fixture: Meeting, user_fixture: User
) -> None:
    # Arrange
    meeting_update = MeetingUpdate(
        name="Updated Team Meeting",
        creation_date=datetime(2024, 9, 29, 16, 0),
        name_platform="COMU",
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        meeting_password="123456",
        meeting_platform_id="123456",
    )
    payload = meeting_update.model_dump()
    headers = get_user_auth_header(user_fixture.keycloak_uuid)

    # Act
    response = meeting_client.put(
        f"/{meeting_fixture.id}", json=payload, headers=headers
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK

    get_after_update_response = meeting_client.get(
        f"/{meeting_fixture.id}", headers=headers
    )

    json_data = get_after_update_response.json()
    assert get_after_update_response.status_code == status.HTTP_200_OK
    assert_json_equal_meeting_model(json_data, meeting_update)  # type: ignore[arg-type]


def test_update_meeting_not_found(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    meeting_update = MeetingUpdate(
        name="Updated Team Meeting",
        creation_date=datetime(2024, 9, 29, 16, 0),
        name_platform="COMU",
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        meeting_password="123456",
        meeting_platform_id="123456",
    )
    payload = meeting_update.model_dump()
    headers = get_user_auth_header(user_fixture.keycloak_uuid)

    # Act
    response = meeting_client.put("/999", json=payload, headers=headers)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_meeting_invalid_input(
    meeting_client: PrefixedTestClient, meeting_fixture: Meeting, user_fixture: User
) -> None:
    # Arrange
    meeting_update = {
        "name": "Updated Team Meeting",
        "creation_date": datetime(2024, 9, 29, 16, 0),
        "name_platform": "COMU",
        "url": "https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        "meeting_password": "123456",
        "meeting_platform_id": "123456",
        "a_wrong_key": "wrong value",
    }

    payload = json.dumps(meeting_update, default=str)
    headers = get_user_auth_header(user_fixture.keycloak_uuid)

    # Act
    response = meeting_client.put(
        f"/{meeting_fixture.id}", json=payload, headers=headers
    )
    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_delete_meeting_success(
    mock_minio: Mock,
    meeting_client: PrefixedTestClient,
    meeting_fixture: Meeting,
    user_fixture: User,
) -> None:
    mock_minio.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "audio.mp3", "LastModified": datetime.now()}]}
    ]

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.delete(f"/{meeting_fixture.id}", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_after_delete_response = meeting_client.get(
        f"/{meeting_fixture.id}", headers=headers
    )
    assert get_after_delete_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_meeting_not_found(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.delete("/999", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_meeting_create_and_generate_presigned_url(
    meeting_client: PrefixedTestClient, user_fixture: User
) -> None:
    # Arrange
    meeting_create = MeetingCreate(
        name="Super important Meeting",
        creation_date=datetime(2024, 9, 29, 16, 0),
        name_platform="COMU",
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
    )

    expected_result = Meeting(
        name=meeting_create.name,
        creation_date=meeting_create.creation_date,
        name_platform=meeting_create.name_platform,
        url=meeting_create.url,
        id=3,
    )

    payload = {
        "meeting_data": meeting_create.model_dump(),
        "presigned_request": {"filename": "100.wav"},
    }

    # Act
    headers = get_user_auth_header(user_fixture.keycloak_uuid)
    response = meeting_client.post(
        "/create_and_generate_presigned_url", json=payload, headers=headers
    )

    # Assert
    json_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert_json_equal_meeting_model(json_data["meeting"], expected_result)


@pytest.mark.parametrize(
    "filename,expected_status",
    [
        ("100.wav", status.HTTP_200_OK),
        ("100.abc", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    ],
)
def test_meeting_generate_presigned_url(
    meeting_client: PrefixedTestClient,
    meeting_fixture: Meeting,
    user_fixture: User,
    filename: str,
    expected_status: int,
) -> None:
    # Arrange
    payload = {"filename": filename}
    headers = get_user_auth_header(user_fixture.keycloak_uuid)

    response = meeting_client.post(
        f"/{meeting_fixture.id}/presigned_url/generate", json=payload, headers=headers
    )
    assert response.status_code == expected_status


def assert_json_equal_meeting_model(
    json_data: dict[str, Any], meeting: Meeting
) -> None:
    assert json_data["name"] == meeting.name
    # SQLite doesn't store time zone so we have to make manual conversion
    assert datetime.fromisoformat(
        json_data["creation_date"]
    ) == meeting.creation_date.replace(tzinfo=timezone.utc)  # type: ignore[union-attr]
    assert json_data["name_platform"] == meeting.name_platform
    assert json_data["url"] == meeting.url
    assert json_data["meeting_password"] == meeting.meeting_password
    assert json_data["meeting_platform_id"] == meeting.meeting_platform_id


def get_user_auth_header(user_keycloak_uuid: UUID4) -> dict[str, str]:
    return {"X-User-keycloak-uuid": str(user_keycloak_uuid)}
