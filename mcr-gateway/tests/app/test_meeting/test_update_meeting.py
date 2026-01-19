import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from mcr_gateway.app.schemas.meeting_schema import MeetingUpdate
from mcr_gateway.app.services.meeting_service import update_meeting_service


@pytest.mark.asyncio
async def test_update_meeting_service_http_error() -> None:
    """
    Test that `update_meeting_service` raises an HTTPException on HTTP error.
    """
    meeting_id = 1
    user_keycloak_uuid = uuid.uuid4()
    meeting_update = MeetingUpdate(
        name="Updated Meeting",
        name_platform="COMU",
        creation_date=datetime(2024, 10, 1, 10, 0, 0),
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        meeting_password="123456",
        meeting_platform_id="123456",
    )

    # Simulate HTTP error
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "HTTP 404 Not Found",
        request=AsyncMock(),
        response=AsyncMock(status_code=404, text="Meeting not found"),
    )

    with patch("httpx.AsyncClient.put", return_value=mock_response):
        with pytest.raises(HTTPException) as exc_info:
            await update_meeting_service(
                meeting_id=meeting_id,
                meeting_update=meeting_update,
                user_keycloak_uuid=user_keycloak_uuid,
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_meeting_service_unexpected_error() -> None:
    """
    Test that `update_meeting_service` raises an HTTPException on unexpected errors.
    """
    meeting_id = 1
    user_keycloak_uuid = uuid.uuid4()

    meeting_update = MeetingUpdate(
        name="Updated Meeting",
        name_platform="COMU",
        creation_date=datetime(2024, 10, 1, 10, 0, 0),
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        meeting_password=None,
        meeting_platform_id=None,
    )

    # Simulate unexpected error
    with patch("httpx.AsyncClient.put", side_effect=Exception("Unexpected error")):
        with pytest.raises(HTTPException) as exc_info:
            await update_meeting_service(
                meeting_id=meeting_id,
                meeting_update=meeting_update,
                user_keycloak_uuid=user_keycloak_uuid,
            )

    assert exc_info.value.status_code == 500
    assert "Unexpected error" in exc_info.value.detail
