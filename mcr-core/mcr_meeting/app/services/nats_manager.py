"""NATS Manager service for handling message publishing and consumption."""

import asyncio
import json
import time
import uuid
from typing import Any, Callable, Dict, Optional

import nats
from loguru import logger
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js import JetStreamContext

from mcr_meeting.app.configs.base import NATSSettings


class NotificationStore:
    """In-memory storage for notifications with user indexing and read/unread tracking."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}  # notification_id -> notification data
        self._user_index: Dict[str, list[str]] = {}  # user_id -> [notification_ids]

    def add(self, notification_id: str, payload: Dict[str, Any]) -> None:
        """Add a notification to the store."""
        # Extract user_id from payload (try both recipient_id and user_id)
        user_id = payload.get("recipient_id") or payload.get("user_id")
        if not user_id:
            logger.warning(f"Notification {notification_id} has no user_id, cannot index")
            return

        self._store[notification_id] = {
            "id": notification_id,
            "title": payload.get("title", ""),
            "content": payload.get("content", ""),
            "type": payload.get("type", "info"),
            "link": payload.get("link"),
            "read": False,
            "timestamp": int(time.time() * 1000),  # milliseconds
            "user_id": user_id,
        }

        # Add to user index
        if user_id not in self._user_index:
            self._user_index[user_id] = []
        self._user_index[user_id].append(notification_id)

        logger.debug(f"Added notification {notification_id} to store for user {user_id}")

    def get(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a notification from the store."""
        return self._store.get(notification_id)

    def get_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Dict[str, Any]]:
        """Get notifications for a specific user."""
        notification_ids = self._user_index.get(user_id, [])

        # Sort by timestamp (newest first)
        sorted_ids = sorted(
            notification_ids,
            key=lambda nid: self._store.get(nid, {}).get("timestamp", 0),
            reverse=True
        )

        # Apply pagination
        paginated_ids = sorted_ids[offset:offset + limit]

        # Return notification data
        return [self._store[nid] for nid in paginated_ids if nid in self._store]

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user."""
        notification_ids = self._user_index.get(user_id, [])
        return sum(
            1 for nid in notification_ids
            if nid in self._store and not self._store[nid].get("read", False)
        )

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read. Returns True if successful."""
        if notification_id in self._store:
            self._store[notification_id]["read"] = True
            logger.debug(f"Marked notification {notification_id} as read")
            return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications for a user as read. Returns count of notifications marked."""
        notification_ids = self._user_index.get(user_id, [])
        count = 0
        for nid in notification_ids:
            if nid in self._store and not self._store[nid].get("read", False):
                self._store[nid]["read"] = True
                count += 1
        logger.debug(f"Marked {count} notifications as read for user {user_id}")
        return count

    def remove(self, notification_id: str) -> None:
        """Remove a notification from the store."""
        if notification_id in self._store:
            # Remove from user index
            user_id = self._store[notification_id].get("user_id")
            if user_id and user_id in self._user_index:
                try:
                    self._user_index[user_id].remove(notification_id)
                except ValueError:
                    pass

            # Remove from store
            del self._store[notification_id]
            logger.debug(f"Removed notification {notification_id} from store")

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all notifications from the store."""
        return self._store.copy()


class NATSManager:
    """Manager for NATS connections and message handling."""

    def __init__(self) -> None:
        """Initialize NATS manager with settings."""
        self.settings = NATSSettings()
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[JetStreamContext] = None
        self.notification_store = NotificationStore()
        self._consumer_task: Optional[asyncio.Task] = None
        self._broadcast_callback: Optional[Callable] = None
        self._is_consuming = False

    async def connect(self) -> None:
        """Connect to NATS server and initialize JetStream."""
        try:
            logger.info(f"Connecting to NATS at {self.settings.NATS_URL}")
            self.nc = await nats.connect(self.settings.NATS_URL)
            self.js = self.nc.jetstream()
            logger.info("Successfully connected to NATS")

            # Ensure stream exists
            await self._ensure_stream()
            # Ensure consumer exists
            await self._ensure_consumer()

        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS server and cleanup."""
        try:
            # Stop consumer task
            if self._consumer_task and not self._consumer_task.done():
                self._is_consuming = False
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    logger.info("Consumer task cancelled successfully")

            # Close NATS connection
            if self.nc and not self.nc.is_closed:
                await self.nc.close()
                logger.info("Disconnected from NATS")

        except Exception as e:
            logger.error(f"Error during NATS disconnect: {e}")

    async def _ensure_stream(self) -> None:
        """Ensure the NATS JetStream stream exists with correct configuration."""
        if not self.js:
            raise RuntimeError("JetStream not initialized")

        from nats.js.api import StreamConfig

        desired_config = StreamConfig(
            name=self.settings.NATS_STREAM,
            subjects=[f"{self.settings.NATS_STREAM}.>"],
            retention="limits",
            max_msgs=1000,
            max_age=86400,  # 24 hours in seconds
        )

        try:
            # Try to get stream info
            stream_info = await self.js.stream_info(self.settings.NATS_STREAM)
            current_subjects = stream_info.config.subjects
            desired_subjects = desired_config.subjects

            # Check if subjects need updating
            if set(current_subjects) != set(desired_subjects):
                logger.info(
                    f"Stream {self.settings.NATS_STREAM} has incorrect subjects: {current_subjects}. Updating to {desired_subjects}"
                )
                # Update the stream
                await self.js.update_stream(desired_config)
                logger.info(f"Updated stream {self.settings.NATS_STREAM}")
            else:
                logger.info(f"Stream {self.settings.NATS_STREAM} already exists with correct configuration")
        except Exception:
            # Stream doesn't exist, create it
            try:
                await self.js.add_stream(desired_config)
                logger.info(f"Created stream {self.settings.NATS_STREAM}")
            except Exception as e:
                logger.error(f"Failed to create stream: {e}")
                raise

    async def _ensure_consumer(self) -> None:
        """Ensure the NATS JetStream consumer exists."""
        if not self.js:
            raise RuntimeError("JetStream not initialized")

        try:
            # Try to get consumer info
            await self.js.consumer_info(
                self.settings.NATS_STREAM, self.settings.NATS_CONSUMER
            )
            logger.info(f"Consumer {self.settings.NATS_CONSUMER} already exists")
        except Exception:
            # Consumer doesn't exist, create it
            try:
                from nats.js.api import ConsumerConfig

                consumer_config = ConsumerConfig(
                    durable_name=self.settings.NATS_CONSUMER,
                    deliver_policy="all",
                    ack_policy="explicit",
                    max_deliver=3,
                    ack_wait=30,  # 30 seconds
                )
                await self.js.add_consumer(
                    self.settings.NATS_STREAM, consumer_config
                )
                logger.info(f"Created consumer {self.settings.NATS_CONSUMER}")
            except Exception as e:
                logger.error(f"Failed to create consumer: {e}")
                raise

    async def publish(
        self, subject: str, payload: Dict[str, Any], notification_id: Optional[str] = None
    ) -> str:
        """
        Publish a notification to NATS.

        Args:
            subject: The subject to publish to (will be prefixed with stream name)
            payload: The notification payload
            notification_id: Optional notification ID (will be generated if not provided)

        Returns:
            The notification ID
        """
        if not self.js:
            raise RuntimeError("JetStream not initialized. Call connect() first.")

        if notification_id is None:
            notification_id = str(uuid.uuid4())

        # Store notification
        self.notification_store.add(notification_id, payload)

        # Build full subject
        full_subject = f"{self.settings.NATS_STREAM}.{subject}"

        # Prepare message with metadata
        message = {
            "id": notification_id,
            "timestamp": time.time(),
            "payload": payload,
        }

        try:
            # Publish to NATS
            ack = await self.js.publish(full_subject, json.dumps(message).encode())
            logger.info(
                f"Published notification {notification_id} to {full_subject}, seq={ack.seq}"
            )
            return notification_id

        except Exception as e:
            logger.error(f"Failed to publish notification: {e}")
            # Remove from store if publish failed
            self.notification_store.remove(notification_id)
            raise

    def set_broadcast_callback(self, callback: Callable) -> None:
        """
        Set the callback function for broadcasting messages to WebSocket clients.

        Args:
            callback: Async function that takes (user_id, message) as arguments
        """
        self._broadcast_callback = callback
        logger.info("WebSocket broadcast callback set")

    async def start_consumer(self) -> None:
        """Start the background consumer task."""
        if self._consumer_task and not self._consumer_task.done():
            logger.warning("Consumer task already running")
            return

        self._is_consuming = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info("Started NATS consumer task")

    async def _consume_loop(self) -> None:
        """Background loop to consume messages from NATS."""
        if not self.js:
            raise RuntimeError("JetStream not initialized")

        try:
            # Subscribe to the consumer
            psub = await self.js.pull_subscribe(
                f"{self.settings.NATS_STREAM}.>",
                self.settings.NATS_CONSUMER,
            )

            logger.info("Consumer loop started, waiting for messages...")

            while self._is_consuming:
                try:
                    # Fetch messages (batch of 1, wait up to 5 seconds)
                    messages = await psub.fetch(batch=1, timeout=5)

                    for msg in messages:
                        try:
                            # Decode and parse message
                            data = json.loads(msg.data.decode())
                            notification_id = data.get("id")
                            payload = data.get("payload", {})

                            logger.info(
                                f"Received notification {notification_id} from NATS"
                            )

                            # Broadcast to WebSocket clients if callback is set
                            if self._broadcast_callback:
                                # Try both recipient_id and user_id for compatibility
                                user_id = payload.get("recipient_id") or payload.get("user_id")
                                if user_id:
                                    # Get the full notification from store to broadcast
                                    notification = self.notification_store.get(notification_id)
                                    if notification:
                                        await self._broadcast_callback(user_id, notification)
                                        logger.debug(
                                            f"Broadcasted notification to user {user_id}"
                                        )
                                    else:
                                        logger.warning(
                                            f"Notification {notification_id} not found in store"
                                        )
                                else:
                                    logger.warning(
                                        f"No recipient_id or user_id in notification {notification_id}"
                                    )

                            # Acknowledge message
                            await msg.ack()

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode message: {e}")
                            await msg.nak()  # Negative acknowledge
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            await msg.nak()

                except NatsTimeoutError:
                    # No messages available, continue waiting
                    continue
                except asyncio.CancelledError:
                    logger.info("Consumer loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            logger.error(f"Fatal error in consumer loop: {e}")
            self._is_consuming = False

        finally:
            logger.info("Consumer loop stopped")


# Global instance
nats_manager = NATSManager()
