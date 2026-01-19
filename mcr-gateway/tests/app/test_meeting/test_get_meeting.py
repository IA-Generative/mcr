import uuid

import pytest
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.services.meeting_service import get_meeting_service


@pytest.mark.asyncio
async def test_get_meeting_service_success(httpx_mock: HTTPXMock) -> None:
    """
    Test that get_meeting_service successfully retrieves a meeting.
    """
    meeting_id = 1
    user_keycloak_uuid = uuid.uuid4()

    mock_meeting_data = {
        "id": meeting_id,
        "name": "Team Meeting",
        "name_platform": "COMU",
        "creation_date": "2024-09-29T10:00:00",
        "url": "https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        "status": "CAPTURE_PENDING",
        "meeting_password": None,
        "meeting_platform_id": None,
    }

    httpx_mock.add_response(
        method="GET",
        url=f"{settings.MEETING_SERVICE_URL}{meeting_id}",
        json=mock_meeting_data,
        status_code=200,
    )

    meeting = await get_meeting_service(meeting_id, user_keycloak_uuid)

    assert meeting.id == meeting_id
    assert meeting.name == "Team Meeting"
    assert meeting.status == "CAPTURE_PENDING"
