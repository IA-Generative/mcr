from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.schemas.lookup_schema import ComuMeetingLookupResponse
from mcr_meeting.main import app

from .conftest import PrefixedTestClient

api_settings = ApiSettings()


@pytest.fixture
def lookup_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.LOOKUP_API_PREFIX)


@patch("mcr_meeting.app.services.lookup_service.ComuClient")
def test_lookup_with_secret_success(
    mock_comu_client_cls: AsyncMock,
    lookup_client: PrefixedTestClient,
) -> None:
    mock_client = mock_comu_client_cls.return_value
    mock_client.lookup_with_secret = AsyncMock(
        return_value=ComuMeetingLookupResponse(name="Réunion d'équipe")
    )

    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457", "secret": "GF2e74BjOcDR1Bq6nvv5wA"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"name": "Réunion d'équipe"}
    mock_client.lookup_with_secret.assert_called_once_with(
        "306356457", "GF2e74BjOcDR1Bq6nvv5wA"
    )


@patch("mcr_meeting.app.services.lookup_service.ComuClient")
def test_lookup_with_passcode_success(
    mock_comu_client_cls: AsyncMock,
    lookup_client: PrefixedTestClient,
) -> None:
    mock_client = mock_comu_client_cls.return_value
    mock_client.lookup_with_passcode = AsyncMock(
        return_value=ComuMeetingLookupResponse(name="Réunion projet")
    )

    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457", "passcode": "123456"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"name": "Réunion projet"}
    mock_client.lookup_with_passcode.assert_called_once_with("306356457", "123456")


def test_lookup_missing_secret_and_passcode(
    lookup_client: PrefixedTestClient,
) -> None:
    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_lookup_with_both_secret_and_passcode(
    lookup_client: PrefixedTestClient,
) -> None:
    response = lookup_client.post(
        "/",
        json={
            "comu_meeting_id": "306356457",
            "secret": "GF2e74BjOcDR1Bq6nvv5wA",
            "passcode": "123456",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@patch("mcr_meeting.app.services.lookup_service.ComuClient")
def test_lookup_comu_api_http_error_is_forwarded(
    mock_comu_client_cls: AsyncMock,
    lookup_client: PrefixedTestClient,
) -> None:
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = "Meeting not found"

    mock_client = mock_comu_client_cls.return_value
    mock_client.lookup_with_secret = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
    )

    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457", "secret": "GF2e74BjOcDR1Bq6nvv5wA"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
