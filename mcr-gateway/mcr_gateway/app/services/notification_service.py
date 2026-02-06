from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

import httpx
from fastapi import HTTPException
from loguru import logger
from pydantic import UUID4

from mcr_gateway.app.configs.config import settings


class MCRCoreCustomAuth(httpx.Auth):
    def __init__(self, user_keycloak_uuid: UUID4):
        self.token = str(user_keycloak_uuid)

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, Any, None]:
        request.headers["X-User-Keycloak-Uuid"] = self.token
        yield request


@asynccontextmanager
async def get_notification_http_client(
    user_keycloak_uuid: UUID4,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    client = httpx.AsyncClient(
        base_url=settings.NOTIFICATION_SERVICE_URL,
        auth=MCRCoreCustomAuth(user_keycloak_uuid),
    )
    try:
        yield client
    finally:
        await client.aclose()


async def get_notifications_service(
    user_keycloak_uuid: UUID4,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Service to retrieve notifications for a user.

    Args:
        user_keycloak_uuid (UUID4): The user's Keycloak UUID.
        limit (Optional[int]): Maximum number of notifications to retrieve.
        offset (Optional[int]): Number of notifications to skip.

    Returns:
        List[Dict[str, Any]]: List of notification objects.
    """
    try:
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        async with get_notification_http_client(user_keycloak_uuid) as client:
            response = await client.get("", params=params)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def get_unread_count_service(
    user_keycloak_uuid: UUID4,
) -> Dict[str, Any]:
    """
    Service to retrieve the count of unread notifications for a user.

    Args:
        user_keycloak_uuid (UUID4): The user's Keycloak UUID.

    Returns:
        Dict[str, Any]: Dictionary containing the unread count.
    """
    try:
        async with get_notification_http_client(user_keycloak_uuid) as client:
            response = await client.get("unread/count")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def send_notification_service(
    notification_data: Dict[str, Any],
    user_keycloak_uuid: UUID4,
) -> Dict[str, Any]:
    """
    Service to send a notification.

    Args:
        notification_data (Dict[str, Any]): The notification data to send.
        user_keycloak_uuid (UUID4): The user's Keycloak UUID.

    Returns:
        Dict[str, Any]: The created notification object.
    """
    try:
        async with get_notification_http_client(user_keycloak_uuid) as client:
            response = await client.post("send", json=notification_data)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def mark_as_read_service(
    notification_id: int,
    user_keycloak_uuid: UUID4,
) -> Dict[str, Any]:
    """
    Service to mark a notification as read.

    Args:
        notification_id (int): The ID of the notification to mark as read.
        user_keycloak_uuid (UUID4): The user's Keycloak UUID.

    Returns:
        Dict[str, Any]: The updated notification object.
    """
    try:
        async with get_notification_http_client(user_keycloak_uuid) as client:
            response = await client.patch(f"{notification_id}")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def mark_all_read_service(
    user_keycloak_uuid: UUID4,
) -> Dict[str, Any]:
    """
    Service to mark all notifications as read for a user.

    Args:
        user_keycloak_uuid (UUID4): The user's Keycloak UUID.

    Returns:
        Dict[str, Any]: Response containing the result of the operation.
    """
    try:
        async with get_notification_http_client(user_keycloak_uuid) as client:
            response = await client.post("mark-all-read")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
