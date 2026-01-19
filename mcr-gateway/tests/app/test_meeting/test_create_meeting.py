import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.meeting_schema import Meeting, MeetingCreate, MeetingStatus
from mcr_gateway.app.services.meeting_service import create_meeting_service


@pytest.mark.asyncio
async def test_create_meeting_service_success(httpx_mock: HTTPXMock) -> None:
    """
    Test that the create_meeting_service function successfully creates a meeting.
    """
    # Arrange
    meeting_data = MeetingCreate(
        name="Team Meeting",
        name_platform="COMU",
        creation_date=datetime(2024, 9, 29, 10, 0, 0),
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
    )
    user_keycloak_uuid = uuid.uuid4()
    mock_response_data = Meeting(
        id=1, status=MeetingStatus.NONE, **meeting_data.model_dump()
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.MEETING_SERVICE_URL}",
        json=mock_response_data.model_dump(mode="json"),
        status_code=201,
    )

    # Act
    result = await create_meeting_service(meeting_data, user_keycloak_uuid)

    # Assert
    # assert result == mock_response_data
    assert result.name == mock_response_data.name
    assert result.creation_date == mock_response_data.creation_date.replace(
        tzinfo=timezone.utc
    )
    assert result.name_platform == mock_response_data.name_platform
    assert result.url == mock_response_data.url
    assert result.meeting_password == mock_response_data.meeting_password
    assert result.meeting_platform_id == mock_response_data.meeting_platform_id


@pytest.mark.asyncio
async def test_create_meeting_service_unexpected_error() -> None:
    """
    Test that create_meeting_service raises an HTTPException on unexpected errors.
    """
    # Arrange
    meeting_data = MeetingCreate(
        name="Team Meeting",
        name_platform="COMU",
        creation_date=datetime(2024, 9, 29, 10, 0, 0),
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
    )
    user_keycloak_uuid = uuid.uuid4()

    # Mocking the unexpected error
    with patch(
        "mcr_gateway.app.services.meeting_service.httpx.AsyncClient.post",
        side_effect=Exception("Unexpected error"),
    ):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_meeting_service(meeting_data, user_keycloak_uuid)
        assert exc_info.value.status_code == 500
        assert "Unexpected error" in exc_info.value.detail
