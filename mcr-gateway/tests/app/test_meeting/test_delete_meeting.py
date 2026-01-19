import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from mcr_gateway.app.services.meeting_service import delete_meeting_service


@pytest.mark.asyncio
async def test_delete_meeting_service_success() -> None:
    """
    Test that `delete_meeting_service` successfully deletes a meeting.
    """
    meeting_id = 1
    user_keycloak_uuid = uuid.uuid4()

    # Mock the httpx.AsyncClient.delete method
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.delete", return_value=mock_response):
        result = await delete_meeting_service(
            meeting_id, user_keycloak_uuid=user_keycloak_uuid
        )

    assert result is None


@pytest.mark.asyncio
async def test_delete_meeting_service_unexpected_error() -> None:
    """
    Test that `delete_meeting_service` raises an HTTPException on unexpected errors.
    """
    meeting_id = 1
    user_keycloak_uuid = uuid.uuid4()

    # Simulate unexpected error
    with patch("httpx.AsyncClient.delete", side_effect=Exception("Unexpected error")):
        with pytest.raises(HTTPException) as exc_info:
            await delete_meeting_service(
                meeting_id, user_keycloak_uuid=user_keycloak_uuid
            )

    assert exc_info.value.status_code == 500
    assert "Unexpected error" in exc_info.value.detail
