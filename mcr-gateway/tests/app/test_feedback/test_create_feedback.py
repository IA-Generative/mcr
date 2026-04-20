import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.feedback_schema import Feedback, FeedbackRequest, VoteType
from mcr_gateway.app.services.feedback_service import create_feedback_service


@pytest.mark.asyncio
async def test_create_feedback_service_success(httpx_mock: HTTPXMock) -> None:
    # Arrange
    feedback_data = FeedbackRequest(
        vote_type=VoteType.POSITIVE,
        url="https://app.example.com/meetings/1",
        comment="Très utile !",
    )
    user_keycloak_uuid = uuid.uuid4()
    mock_response = Feedback(
        id=42,
        user_id=7,
        meeting_id=1,
        vote_type=VoteType.POSITIVE,
        comment="Très utile !",
        created_at=datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    httpx_mock.add_response(
        method="POST",
        url=settings.FEEDBACK_SERVICE_URL,
        json=mock_response.model_dump(mode="json"),
        status_code=201,
    )

    # Act
    result = await create_feedback_service(feedback_data, user_keycloak_uuid)

    # Assert
    assert result.id == mock_response.id
    assert result.vote_type == VoteType.POSITIVE
    assert result.comment == mock_response.comment


@pytest.mark.asyncio
async def test_create_feedback_service_http_error(httpx_mock: HTTPXMock) -> None:
    # Arrange
    feedback_data = FeedbackRequest(
        vote_type=VoteType.NEGATIVE,
        url="https://app.example.com/",
    )
    user_keycloak_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="POST",
        url=settings.FEEDBACK_SERVICE_URL,
        status_code=422,
        text="Unprocessable Entity",
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_feedback_service(feedback_data, user_keycloak_uuid)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_feedback_service_unexpected_error() -> None:
    # Arrange
    feedback_data = FeedbackRequest(
        vote_type=VoteType.POSITIVE,
        url="https://app.example.com/",
    )
    user_keycloak_uuid = uuid.uuid4()

    with patch(
        "mcr_gateway.app.services.feedback_service.httpx.AsyncClient.post",
        side_effect=Exception("Unexpected error"),
    ):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_feedback_service(feedback_data, user_keycloak_uuid)
        assert exc_info.value.status_code == 500
        assert "Unexpected error" in exc_info.value.detail
