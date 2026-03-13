from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.services.feature_flag_service import (
    is_feature_enabled,
    is_get_meeting_audio_enabled,
)

# ──────────────────────────────────────────────
# is_feature_enabled
# ──────────────────────────────────────────────

FAKE_FLAG = "test_flag"


@pytest.mark.asyncio
async def test_is_feature_enabled_returns_true(httpx_mock: HTTPXMock) -> None:
    """Flag enabled → returns True."""
    # Arrange
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.CORE_SERVICE_BASE_URL}/api/feature-flag/{FAKE_FLAG}",
        json=True,
        status_code=200,
    )

    # Act
    result = await is_feature_enabled(FAKE_FLAG)

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_is_feature_enabled_returns_false(httpx_mock: HTTPXMock) -> None:
    """Flag disabled → returns False."""
    # Arrange
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.CORE_SERVICE_BASE_URL}/api/feature-flag/{FAKE_FLAG}",
        json=False,
        status_code=200,
    )

    # Act
    result = await is_feature_enabled(FAKE_FLAG)

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_is_feature_enabled_http_error(httpx_mock: HTTPXMock) -> None:
    """HTTP Error 500 → raises httpx.HTTPStatusError."""
    # Arrange
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.CORE_SERVICE_BASE_URL}/api/feature-flag/{FAKE_FLAG}",
        status_code=500,
    )

    # Act & Assert
    with pytest.raises(httpx.HTTPStatusError):
        await is_feature_enabled(FAKE_FLAG)


@pytest.mark.asyncio
async def test_is_feature_enabled_unexpected_error() -> None:
    """Unexpected network error → spreads the exception"""
    # Arrange
    with patch(
        "mcr_gateway.app.services.feature_flag_service.httpx.AsyncClient.get",
        side_effect=Exception("Connection refused"),
    ):
        # Act & Assert
        with pytest.raises(Exception, match="Connection refused"):
            await is_feature_enabled(FAKE_FLAG)


# ──────────────────────────────────────────────
# is_get_meeting_audio_enabled
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_get_meeting_audio_enabled_when_on() -> None:
    """Flag enabled → doesn't raise an exception."""
    # Arrange
    with patch(
        "mcr_gateway.app.services.feature_flag_service.is_feature_enabled",
        new_callable=AsyncMock,
        return_value=True,
    ):
        # Act & Assert — ne doit rien lever
        await is_get_meeting_audio_enabled()


@pytest.mark.asyncio
async def test_is_get_meeting_audio_enabled_when_off() -> None:
    """Flag disabled → raises HTTPException 403."""
    # Arrange
    with patch(
        "mcr_gateway.app.services.feature_flag_service.is_feature_enabled",
        new_callable=AsyncMock,
        return_value=False,
    ):
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await is_get_meeting_audio_enabled()

        # Assert
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_is_get_meeting_audio_enabled_propagates_error() -> None:
    """Exception in is_feature_enabled → spreads the exception."""
    # Arrange
    with patch(
        "mcr_gateway.app.services.feature_flag_service.is_feature_enabled",
        new_callable=AsyncMock,
        side_effect=Exception("Service unavailable"),
    ):
        # Act & Assert
        with pytest.raises(Exception, match="Service unavailable"):
            await is_get_meeting_audio_enabled()
