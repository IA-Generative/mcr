from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.main import app
from tests.api.conftest import PrefixedTestClient

api_settings = ApiSettings()


@pytest.fixture
def lookup_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.LOOKUP_API_PREFIX)


@pytest.fixture
def mock_comu_http(mocker: MockerFixture) -> tuple[AsyncMock, Mock]:
    """Fake the external httpx call made by infrastructure.comu.

    Returns the mocked async client (to assert the outgoing request) and the
    mocked response (to configure the payload or trigger an error).
    """
    mock_client = AsyncMock()
    mock_response = Mock(spec=httpx.Response)
    mock_client.post.return_value = mock_response

    async_client_cls = mocker.patch(
        "mcr_meeting.app.infrastructure.comu.httpx.AsyncClient"
    )
    async_client_cls.return_value.__aenter__.return_value = mock_client
    async_client_cls.return_value.__aexit__.return_value = None
    return mock_client, mock_response


def test_lookup_with_secret_success(
    mock_comu_http: tuple[AsyncMock, Mock],
    lookup_client: PrefixedTestClient,
) -> None:
    mock_client, mock_response = mock_comu_http
    mock_response.json.return_value = {"name": "Réunion d'équipe"}

    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457", "secret": "GF2e74BjOcDR1Bq6nvv5wA"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"name": "Réunion d'équipe"}
    mock_client.post.assert_awaited_once_with(
        "",
        headers={"Content-Type": "application/json"},
        json={"numericId": "306356457", "secret": "GF2e74BjOcDR1Bq6nvv5wA"},
    )


def test_lookup_with_passcode_success(
    mock_comu_http: tuple[AsyncMock, Mock],
    lookup_client: PrefixedTestClient,
) -> None:
    mock_client, mock_response = mock_comu_http
    mock_response.json.return_value = {"name": "Réunion projet"}

    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457", "passcode": "123456"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"name": "Réunion projet"}
    mock_client.post.assert_awaited_once_with(
        "",
        headers={"Content-Type": "application/json"},
        json={"numericId": "306356457", "passcode": "123456"},
    )


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


def test_lookup_comu_api_http_error_is_forwarded(
    mock_comu_http: tuple[AsyncMock, Mock],
    lookup_client: PrefixedTestClient,
) -> None:
    _, mock_response = mock_comu_http
    error_response = Mock(spec=httpx.Response)
    error_response.status_code = 404
    error_response.text = "Meeting not found"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=error_response
    )

    response = lookup_client.post(
        "/",
        json={"comu_meeting_id": "306356457", "secret": "GF2e74BjOcDR1Bq6nvv5wA"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
