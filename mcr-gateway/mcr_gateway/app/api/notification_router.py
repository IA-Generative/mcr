import asyncio
from typing import Any, Dict, List, Optional

import httpx
import websockets
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.notification_service import (
    get_notifications_service,
    get_unread_count_service,
    mark_all_read_service,
    mark_as_read_service,
    send_notification_service,
)

router = APIRouter()


@router.get(
    "/notifications",
    response_model=List[Dict[str, Any]],
    tags=["Notifications"],
)
async def get_notifications(
    limit: Optional[int] = Query(
        None, description="Maximum number of notifications to retrieve"
    ),
    offset: Optional[int] = Query(None, description="Number of notifications to skip"),
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> List[Dict[str, Any]]:
    """
    Endpoint to retrieve notifications for the current user.

    Args:
        limit (Optional[int]): Maximum number of notifications to retrieve.
        offset (Optional[int]): Number of notifications to skip.
        current_user (TokenUser): The authenticated user.

    Returns:
        List[Dict[str, Any]]: List of notification objects.
    """
    try:
        result = await get_notifications_service(
            user_keycloak_uuid=current_user.keycloak_uuid,
            limit=limit,
            offset=offset,
        )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/notifications/unread/count",
    response_model=Dict[str, Any],
    tags=["Notifications"],
)
async def get_unread_count(
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Dict[str, Any]:
    """
    Endpoint to retrieve the count of unread notifications for the current user.

    Args:
        current_user (TokenUser): The authenticated user.

    Returns:
        Dict[str, Any]: Dictionary containing the unread count.
    """
    try:
        result = await get_unread_count_service(
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notifications/send",
    response_model=Dict[str, Any],
    tags=["Notifications"],
)
async def send_notification(
    notification_data: Dict[str, Any],
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Dict[str, Any]:
    """
    Endpoint to send a notification.

    Args:
        notification_data (Dict[str, Any]): The notification data to send.
        current_user (TokenUser): The authenticated user.

    Returns:
        Dict[str, Any]: The created notification object.
    """
    try:
        result = await send_notification_service(
            notification_data=notification_data,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/notifications/{notification_id}",
    response_model=Dict[str, Any],
    tags=["Notifications"],
)
async def mark_as_read(
    notification_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Dict[str, Any]:
    """
    Endpoint to mark a notification as read.

    Args:
        notification_id (int): The ID of the notification to mark as read.
        current_user (TokenUser): The authenticated user.

    Returns:
        Dict[str, Any]: The updated notification object.
    """
    try:
        result = await mark_as_read_service(
            notification_id=notification_id,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return result
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Notification not found")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notifications/mark-all-read",
    response_model=Dict[str, Any],
    tags=["Notifications"],
)
async def mark_all_read(
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Dict[str, Any]:
    """
    Endpoint to mark all notifications as read for the current user.

    Args:
        current_user (TokenUser): The authenticated user.

    Returns:
        Dict[str, Any]: Response containing the result of the operation.
    """
    try:
        result = await mark_all_read_service(
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/notifications/ws")
async def websocket_proxy(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket proxy endpoint that forwards connections to the backend.

    Args:
        websocket: The client WebSocket connection
        token: JWT token for authentication (optional for now)
    """
    await websocket.accept()
    logger.info("Gateway WebSocket connection accepted")

    # Extract user_id from token (for now, use a placeholder)
    # In production, decode JWT token to get user_id
    user_id = "f0062539-f6df-449a-adcb-a78ef5d9524f"  # TODO: Extract from JWT

    # Connect to backend WebSocket (use service URL from config)
    backend_host = settings.CORE_SERVICE_BASE_URL.replace("http://", "").replace(
        "https://", ""
    )
    backend_ws_url = (
        f"ws://{backend_host}/api/notifications/ws?x_user_keycloak_uuid={user_id}"
    )
    logger.info(f"Connecting to backend WebSocket: {backend_ws_url}")

    try:
        async with websockets.connect(backend_ws_url) as backend_ws:
            logger.info(f"Connected to backend WebSocket for user {user_id}")

            # Create tasks for bidirectional message forwarding
            async def forward_to_backend():
                """Forward messages from client to backend"""
                try:
                    while True:
                        message = await websocket.receive_text()
                        await backend_ws.send(message)
                        logger.debug(f"Forwarded message to backend: {message}")
                except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
                    logger.info("Client disconnected")

            async def forward_to_client():
                """Forward messages from backend to client"""
                try:
                    while True:
                        message = await backend_ws.recv()
                        await websocket.send_text(message)
                        logger.debug(f"Forwarded message to client: {message}")
                except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
                    logger.info("Backend disconnected")

            # Run both forwarding tasks concurrently
            await asyncio.gather(
                forward_to_backend(), forward_to_client(), return_exceptions=True
            )

    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info("Gateway WebSocket connection closed")
