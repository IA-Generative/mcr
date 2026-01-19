from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Generator

import httpx
from fastapi import HTTPException
from loguru import logger
from pydantic import UUID4

from mcr_gateway.app.configs.config import settings


class MCRCoreCustomAuth(httpx.Auth):
    def __init__(self, token: UUID4):
        self.token = str(token)

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["X-User-Keycloak-Uuid"] = self.token
        yield request


@asynccontextmanager
async def get_meeting_http_client(
    user_keycloak_uuid: UUID4,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    client = httpx.AsyncClient(
        base_url=settings.MEETING_SERVICE_URL,
        auth=MCRCoreCustomAuth(user_keycloak_uuid),
    )
    try:
        yield client
    finally:
        await client.aclose()


async def get_transcription_waiting_time_service(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> Dict[str, Any]:
    """
    Service to get the estimated waiting time for the transcription of a given meeting.

    Args:
        meeting_id (int): The ID of the meeting for which to calculate the waiting time
        user_keycloak_uuid (UUID4): The UUID of the authenticated user

    Returns:
        Dict[str, Any]: Contains the estimated waiting time in minutes

    Raises:
        HTTPException: If the API call fails
    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.get(f"{meeting_id}/transcription/wait-time")
            response.raise_for_status()
            json_response: Dict[str, Any] = response.json()
            return json_response
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error getting transcription waiting time: {} - {}",
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error getting transcription waiting time: {}", str(e))
        raise HTTPException(status_code=500, detail="Unexpected error occurred")


async def get_queue_estimated_waiting_time_service(
    user_keycloak_uuid: UUID4,
) -> Dict[str, Any]:
    """
    Service to get the current global waiting time for transcription queue.

    Args:
        user_keycloak_uuid (UUID4): The UUID of the authenticated user

    Returns:
        Dict[str, Any]: Contains the current global waiting time in minutes

    Raises:
        HTTPException: If the API call fails
    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.get("/transcription/wait-time/estimation")
            response.raise_for_status()
            json_response: Dict[str, Any] = response.json()
            return json_response
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error getting global transcription waiting time: {} - {}",
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(
            "Unexpected error getting global transcription waiting time: {}", str(e)
        )
        raise HTTPException(status_code=500, detail="Unexpected error occurred")
