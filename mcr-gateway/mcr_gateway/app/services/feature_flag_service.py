from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import StrEnum
from venv import logger

import httpx
from fastapi import HTTPException

from mcr_gateway.app.configs.config import settings


class FeatureFlag(StrEnum):
    """Centralized enum for all feature flag names in the application."""

    GET_MEETING_AUDIO = "get_meeting_audio"


@asynccontextmanager
async def get_ff_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    client = httpx.AsyncClient(
        base_url=settings.CORE_SERVICE_BASE_URL,
    )
    try:
        yield client
    finally:
        await client.aclose()


async def is_feature_enabled(flag_name: str) -> bool:
    async with get_ff_http_client() as client:
        response = await client.get(f"/api/feature-flag/{flag_name}")
        response.raise_for_status()
        logger.info(response.json())

        result: bool = response.json()
        return result


async def is_get_meeting_audio_enabled() -> None:
    if not await is_feature_enabled(FeatureFlag.GET_MEETING_AUDIO):
        raise HTTPException(
            status_code=403, detail="The feature flag of this feature is OFF"
        )
