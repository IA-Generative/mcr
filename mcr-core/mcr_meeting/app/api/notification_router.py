from typing import List

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.schemas.notification_schema import (
    NotificationCreate,
    NotificationResponse,
)
from mcr_meeting.app.services.nats_manager import nats_manager
from mcr_meeting.app.services.websocket_manager import ws_manager

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.NOTIFICATION_API_PREFIX,
    tags=["Notifications"],
)


@router.post("/send", status_code=202)
async def send_notification(notification: NotificationCreate):
    """
    Send a notification to a user via NATS.

    Args:
        notification (NotificationCreate): The notification to send.

    Returns:
        dict: Status message confirming the notification was queued.
    """
    try:
        message_id = await nats_manager.publish(
            subject=f"notifications.{notification.recipient_id}",
            payload=notification.model_dump(),
        )
        logger.info("Notification queued for user {}", notification.recipient_id)
        return {
            "status": "queued",
            "message_id": message_id,
            "recipient_id": notification.recipient_id,
        }
    except Exception as e:
        logger.error("Failed to send notification: {}", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to send notification: {str(e)}"
        )


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 50,
    offset: int = 0,
    x_user_keycloak_uuid: UUID4 = Header(),
):
    """
    Get notifications for the current user.

    Args:
        limit (int): Maximum number of notifications to return (default: 50).
        offset (int): Number of notifications to skip (default: 0).
        x_user_keycloak_uuid (UUID4): The authenticated user's keycloak UUID from header.

    Returns:
        List[NotificationResponse]: List of notifications.
    """
    user_id = str(x_user_keycloak_uuid)

    try:
        logger.info(
            "Fetching notifications for user {} (limit={}, offset={})",
            user_id,
            limit,
            offset,
        )
        notifications = nats_manager.notification_store.get_by_user(
            user_id, limit, offset
        )
        return notifications
    except Exception as e:
        logger.error("Failed to get notifications: {}", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get notifications: {str(e)}"
        )


@router.get("/unread/count")
async def get_unread_count(x_user_keycloak_uuid: UUID4 = Header()):
    """
    Get the count of unread notifications for the current user.

    Args:
        x_user_keycloak_uuid (UUID4): The authenticated user's keycloak UUID from header.

    Returns:
        dict: Count of unread notifications.
    """
    user_id = str(x_user_keycloak_uuid)

    try:
        logger.info("Fetching unread count for user {}", user_id)
        count = nats_manager.notification_store.get_unread_count(user_id)
        return {"unread_count": count}
    except Exception as e:
        logger.error("Failed to get unread count: {}", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get unread count: {str(e)}"
        )


@router.patch("/{notification_id}")
async def mark_notification_as_read(
    notification_id: str,
    x_user_keycloak_uuid: UUID4 = Header(),
):
    """
    Mark a notification as read.

    Args:
        notification_id (str): The ID of the notification to mark as read.
        x_user_keycloak_uuid (UUID4): The authenticated user's keycloak UUID from header.

    Returns:
        dict: Status message confirming the notification was marked as read.
    """
    user_id = str(x_user_keycloak_uuid)

    try:
        logger.info(
            "Marking notification {} as read for user {}", notification_id, user_id
        )
        success = nats_manager.notification_store.mark_as_read(notification_id)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")

        # Return the updated notification
        notification = nats_manager.notification_store.get(notification_id)
        return notification
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark notification as read: {}", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(x_user_keycloak_uuid: UUID4 = Header()):
    """
    Mark all notifications as read for the current user.

    Args:
        x_user_keycloak_uuid (UUID4): The authenticated user's keycloak UUID from header.

    Returns:
        dict: Status message and count of notifications marked as read.
    """
    user_id = str(x_user_keycloak_uuid)

    try:
        logger.info("Marking all notifications as read for user {}", user_id)
        marked_count = nats_manager.notification_store.mark_all_read(user_id)
        return {"status": "success", "marked_count": marked_count}
    except Exception as e:
        logger.error("Failed to mark all notifications as read: {}", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark all notifications as read: {str(e)}",
        )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    x_user_keycloak_uuid: str | None = None,
    token: str | None = None,
):
    """
    WebSocket endpoint for real-time notification delivery.

    Args:
        websocket (WebSocket): The WebSocket connection.
        x_user_keycloak_uuid (str | None): The authenticated user's keycloak UUID from query parameter.
        token (str | None): JWT token (alternative to x_user_keycloak_uuid).
    """
    # Try to get user_id from direct UUID parameter first
    user_id = x_user_keycloak_uuid

    # If not provided, try to decode JWT token to get user_id
    if not user_id and token:
        try:
            # Decode JWT token (without verification for now - just extract payload)
            import base64
            import json
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) == 3:
                # Decode payload (add padding if needed)
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)  # Add padding
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded)
                user_id = token_data.get('sub')  # 'sub' claim contains user ID
                logger.debug("Extracted user_id from token: {}", user_id)
        except Exception as e:
            logger.warning("Failed to decode token: {}", e)

    # Default to anonymous if no user_id found
    if not user_id:
        user_id = "anonymous"

    await ws_manager.connect(websocket, user_id)
    logger.info("WebSocket connected for user {}", user_id)

    try:
        while True:
            # Keep the connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.debug("Received message from user {}: {}", user_id, data)

            # Echo back or handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
        logger.info("WebSocket disconnected for user {}", user_id)
    except Exception as e:
        logger.error("WebSocket error for user {}: {}", user_id, e)
        await ws_manager.disconnect(user_id)
