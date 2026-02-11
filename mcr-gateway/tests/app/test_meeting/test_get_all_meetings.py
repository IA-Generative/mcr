import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from mcr_gateway.app.services.meeting_service import get_meetings_service

# @pytest.mark.asyncio
# async def test_get_meetings_service_success():
#     """
#     Test que `get_meetings_service` retourne une liste de réunions avec succès.
#     """
#     # Arrange
#     mock_response_data = [
#         {
#             "id": 1,
#             "name": "Team Meeting",
#             "name_platform": "COMU",
#             "creation_date": "2024-09-29T10:00:00",
#             "url": "https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
#             "meeting_password": "password123",
#             "meeting_platform_id": "platform123",
#             "status": "PENDING",
#         }
#     ]
#     user_id = 1
#     search = "Team"

#     mock_response = AsyncMock()
#     mock_response.raise_for_status.return_value = None
#     mock_response.json.return_value = mock_response_data

#     with patch("httpx.AsyncClient.get", return_value=mock_response):
#         # Act
#         meetings = await get_meetings_service(search=search, user_id=user_id)

#     # Assert
#     assert len(meetings) == 1
#     assert meetings[0].id == 1
#     assert meetings[0].name == "Team Meeting"
#     assert meetings[0].name_platform == "COMU"


@pytest.mark.asyncio
async def test_get_meetings_service_unexpected_error() -> None:
    """
    Test que `get_meetings_service` lève une `HTTPException` lors d'une erreur inattendue.
    """
    # Arrange
    user_keycloak_uuid = uuid.uuid4()
    search = "Team"
    with patch("httpx.AsyncClient.get", side_effect=Exception("Unexpected error")):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_meetings_service(
                search=search,
                page=1,
                page_size=10,
                user_keycloak_uuid=user_keycloak_uuid,
            )

        # Assert
        assert exc_info.value.status_code == 500
        assert "Unexpected error" in exc_info.value.detail
