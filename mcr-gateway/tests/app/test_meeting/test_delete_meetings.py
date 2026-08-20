import uuid
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from mcr_gateway.app.services.meeting_service import delete_meetings_service


@pytest.mark.asyncio
async def test_delete_meetings_service_asks_core_once_for_the_whole_list() -> None:
    """
    Test that `delete_meetings_service` forwards every id in a single core call.
    """
    user_keycloak_uuid = uuid.uuid4()

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", return_value=mock_response) as mock_request:
        await delete_meetings_service(
            meeting_ids=[101, 102, 103], user_keycloak_uuid=user_keycloak_uuid
        )

    mock_request.assert_called_once_with("DELETE", "", json={"ids": [101, 102, 103]})


@pytest.mark.asyncio
async def test_delete_meetings_service_forwards_the_core_error_status() -> None:
    """
    Test that `delete_meetings_service` reports the status core answered with.
    """
    user_keycloak_uuid = uuid.uuid4()

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "HTTP 404 Not Found",
        request=AsyncMock(),
        response=AsyncMock(status_code=404, text="Meeting not found"),
    )

    with patch("httpx.AsyncClient.request", return_value=mock_response):
        with pytest.raises(HTTPException) as exc_info:
            await delete_meetings_service(
                meeting_ids=[101], user_keycloak_uuid=user_keycloak_uuid
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_meetings_service_unexpected_error() -> None:
    """
    Test that `delete_meetings_service` raises an HTTPException on unexpected errors.
    """
    user_keycloak_uuid = uuid.uuid4()

    with patch("httpx.AsyncClient.request", side_effect=Exception("Unexpected error")):
        with pytest.raises(HTTPException) as exc_info:
            await delete_meetings_service(
                meeting_ids=[101], user_keycloak_uuid=user_keycloak_uuid
            )

    assert exc_info.value.status_code == 500
    assert "Unexpected error" in exc_info.value.detail
