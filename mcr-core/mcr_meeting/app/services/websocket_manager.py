"""WebSocket Manager service for handling WebSocket connections and broadcasting."""

from typing import Any, Dict, List

from fastapi import WebSocket
from loguru import logger


class WebSocketManager:
    """Manager for WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        """Initialize WebSocket manager with empty connections."""
        # Dictionary mapping user_id to list of WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Accept and register a WebSocket connection for a user.

        Args:
            websocket: The WebSocket connection to register
            user_id: The user ID associated with this connection
        """
        await websocket.accept()

        if user_id not in self._connections:
            self._connections[user_id] = []

        self._connections[user_id].append(websocket)
        logger.info(
            f"WebSocket connected for user {user_id}. "
            f"Total connections for user: {len(self._connections[user_id])}"
        )

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Unregister a WebSocket connection for a user.

        Args:
            websocket: The WebSocket connection to unregister
            user_id: The user ID associated with this connection
        """
        if user_id in self._connections:
            if websocket in self._connections[user_id]:
                self._connections[user_id].remove(websocket)
                logger.info(
                    f"WebSocket disconnected for user {user_id}. "
                    f"Remaining connections for user: {len(self._connections[user_id])}"
                )

                # Clean up empty user entries
                if not self._connections[user_id]:
                    del self._connections[user_id]
                    logger.debug(f"Removed user {user_id} from connections (no active connections)")

    async def send_to_user(self, user_id: str, message: Any) -> None:
        """
        Broadcast a message to all WebSocket connections for a specific user.

        Args:
            user_id: The user ID to send the message to
            message: The message to send (will be sent as JSON)
        """
        if user_id not in self._connections:
            logger.debug(f"No active connections for user {user_id}")
            return

        # Get list of connections for the user
        connections = self._connections[user_id].copy()
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.debug(f"Sent message to user {user_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to send message to user {user_id}: {e}. "
                    "Marking connection for removal."
                )
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket, user_id)

    def get_active_users(self) -> List[str]:
        """
        Get a list of all users with active WebSocket connections.

        Returns:
            List of user IDs with active connections
        """
        return list(self._connections.keys())

    def get_connection_count(self, user_id: str) -> int:
        """
        Get the number of active connections for a specific user.

        Args:
            user_id: The user ID to check

        Returns:
            Number of active connections for the user
        """
        return len(self._connections.get(user_id, []))

    def get_total_connections(self) -> int:
        """
        Get the total number of active WebSocket connections.

        Returns:
            Total number of active connections across all users
        """
        return sum(len(conns) for conns in self._connections.values())


# Global instance
ws_manager = WebSocketManager()
