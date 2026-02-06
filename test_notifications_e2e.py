#!/usr/bin/env python3
"""
End-to-End Integration Tests for Notification System

Tests the complete notification flow:
- HTTP API via gateway (localhost:8000)
- WebSocket via gateway (localhost:8000)
- NATS message broker
- Real-time notification delivery

# /// script
# dependencies = [
#   "httpx",
#   "websockets",
# ]
# ///
"""

import asyncio
import json
import uuid
from typing import Optional

import httpx
import websockets


# Test Configuration
BACKEND_BASE_URL = "http://localhost:8001"  # Test backend directly first
BACKEND_WS_URL = "ws://localhost:8001"
GATEWAY_BASE_URL = "http://localhost:8000"
GATEWAY_WS_URL = "ws://localhost:8000"
TEST_USER_UUID = "f0062539-f6df-449a-adcb-a78ef5d9524f"
TEST_USER_EMAIL = "fake@fake.com"

# For backend testing, we use simple header auth
# For gateway testing, we'll need JWT token
USE_GATEWAY = False  # Use backend for HTTP
USE_GATEWAY_WEBSOCKET = True  # Use gateway for WebSocket proxy


class NotificationTestClient:
    """Helper client for notification API testing."""

    def __init__(self, user_uuid: str, use_gateway: bool = USE_GATEWAY, use_gateway_ws: bool = USE_GATEWAY_WEBSOCKET):
        self.user_uuid = user_uuid
        self.use_gateway = use_gateway
        self.use_gateway_ws = use_gateway_ws
        self.base_url = GATEWAY_BASE_URL if use_gateway else BACKEND_BASE_URL
        self.ws_url = GATEWAY_WS_URL if use_gateway_ws else BACKEND_WS_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-User-Keycloak-Uuid": user_uuid,
        }

    async def send_notification(
        self,
        title: str,
        content: str,
        type_: str = "info",
        link: Optional[str] = None
    ) -> dict:
        """Send a notification via HTTP POST."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            payload = {
                "recipient_id": self.user_uuid,
                "title": title,
                "content": content,
                "type": type_,
            }
            if link:
                payload["link"] = link

            response = await client.post(
                f"{self.base_url}/api/notifications/send",
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    async def list_notifications(self, limit: int = 50, offset: int = 0) -> list:
        """List notifications via HTTP GET."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{self.base_url}/api/notifications",
                params={"limit": limit, "offset": offset},
                headers=self.headers,
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_unread_count(self) -> int:
        """Get unread notification count."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{self.base_url}/api/notifications/unread/count",
                headers=self.headers,
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("count") or data.get("unread_count", 0)

    async def mark_as_read(self, notification_id: str) -> dict:
        """Mark a notification as read."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.patch(
                f"{self.base_url}/api/notifications/{notification_id}",
                headers=self.headers,
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    async def mark_all_read(self) -> dict:
        """Mark all notifications as read."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                f"{self.base_url}/api/notifications/mark-all-read",
                headers=self.headers,
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()

    async def connect_websocket(self, token: Optional[str] = None):
        """Connect to WebSocket."""
        if self.use_gateway_ws:
            # Gateway WebSocket proxy (token optional for now)
            ws_url = f"{self.ws_url}/api/notifications/ws"
            if token:
                ws_url += f"?token={token}"
        else:
            # Backend accepts user UUID as query parameter
            ws_url = f"{self.ws_url}/api/notifications/ws?x_user_keycloak_uuid={self.user_uuid}"

        websocket = await asyncio.wait_for(
            websockets.connect(ws_url),
            timeout=5.0
        )
        return websocket


# Test Functions

async def test_1_send_notification():
    """Test 1: Send notification via HTTP POST."""
    print("\n[TEST 1] Send notification via gateway...")

    client = NotificationTestClient(TEST_USER_UUID)

    result = await client.send_notification(
        title="Test Notification",
        content="This is a test notification",
        type_="info"
    )

    assert result["status"] == "queued", f"Expected status 'queued', got {result['status']}"
    assert "message_id" in result, "Missing message_id in response"
    assert result["recipient_id"] == TEST_USER_UUID, "Recipient ID mismatch"

    # Validate message_id is a valid UUID
    try:
        uuid.UUID(result["message_id"])
    except ValueError:
        raise AssertionError(f"Invalid UUID: {result['message_id']}")

    print(f"✓ Notification sent: {result['message_id']}")
    return result


async def test_2_list_notifications():
    """Test 2: List notifications via HTTP GET."""
    print("\n[TEST 2] List notifications via gateway...")

    client = NotificationTestClient(TEST_USER_UUID)

    # Send a notification first
    sent = await client.send_notification(
        title="Test List",
        content="Testing list endpoint"
    )

    # Wait a bit for NATS processing
    await asyncio.sleep(1)

    # List notifications
    notifications = await client.list_notifications(limit=10)

    assert isinstance(notifications, list), "Expected list response"
    assert len(notifications) > 0, "Expected at least one notification"

    # Find our notification
    found = False
    for notif in notifications:
        if notif.get("id") == sent["message_id"]:
            found = True
            assert notif["title"] == "Test List"
            assert notif["content"] == "Testing list endpoint"
            assert notif["type"] == "info"
            assert "timestamp" in notif
            assert isinstance(notif["read"], bool)
            break

    assert found, f"Notification {sent['message_id']} not found in list"

    print(f"✓ Listed {len(notifications)} notification(s)")
    return notifications


async def test_3_unread_count():
    """Test 3: Get unread notification count."""
    print("\n[TEST 3] Get unread count...")

    client = NotificationTestClient(TEST_USER_UUID)

    # Get initial count
    initial_count = await client.get_unread_count()
    print(f"  Initial unread count: {initial_count}")

    # Send a notification
    await client.send_notification(
        title="Unread Test",
        content="Testing unread count"
    )

    # Wait for processing
    await asyncio.sleep(1)

    # Get new count
    new_count = await client.get_unread_count()
    print(f"  New unread count: {new_count}")

    assert new_count > initial_count, f"Expected count to increase from {initial_count} to {new_count}"

    print(f"✓ Unread count increased: {initial_count} -> {new_count}")
    return new_count


async def test_4_mark_as_read():
    """Test 4: Mark notification as read."""
    print("\n[TEST 4] Mark notification as read...")

    client = NotificationTestClient(TEST_USER_UUID)

    # Send a notification
    sent = await client.send_notification(
        title="Read Test",
        content="Testing mark as read"
    )

    await asyncio.sleep(1)

    # Get unread count before
    count_before = await client.get_unread_count()

    # Mark as read
    result = await client.mark_as_read(sent["message_id"])

    assert result["read"] is True, "Notification should be marked as read"

    # Get unread count after
    count_after = await client.get_unread_count()

    assert count_after < count_before, f"Unread count should decrease from {count_before} to {count_after}"

    print(f"✓ Marked as read, unread count: {count_before} -> {count_after}")


async def test_5_mark_all_read():
    """Test 5: Mark all notifications as read."""
    print("\n[TEST 5] Mark all notifications as read...")

    client = NotificationTestClient(TEST_USER_UUID)

    # Send multiple notifications
    for i in range(3):
        await client.send_notification(
            title=f"Batch Test {i+1}",
            content=f"Testing batch read {i+1}"
        )

    await asyncio.sleep(1)

    # Get count before
    count_before = await client.get_unread_count()
    print(f"  Unread before: {count_before}")

    # Mark all as read
    result = await client.mark_all_read()

    # Get count after
    count_after = await client.get_unread_count()
    print(f"  Unread after: {count_after}")

    assert count_after == 0, f"Expected 0 unread, got {count_after}"

    print(f"✓ Marked all as read: {count_before} -> {count_after}")


async def test_6_websocket_connection():
    """Test 6: Connect to WebSocket."""
    print("\n[TEST 6] Connect to WebSocket...")

    client = NotificationTestClient(TEST_USER_UUID)

    try:
        websocket = await client.connect_websocket()
        print(f"✓ WebSocket connected: {websocket.remote_address}")

        # Keep connection alive for a moment
        await asyncio.sleep(0.5)

        await websocket.close()
        print("✓ WebSocket closed cleanly")

    except Exception as e:
        raise AssertionError(f"WebSocket connection failed: {e}")


async def test_7_websocket_receive_notification():
    """Test 7: Receive notification via WebSocket."""
    print("\n[TEST 7] Receive notification via WebSocket...")

    client = NotificationTestClient(TEST_USER_UUID)

    # Connect WebSocket
    websocket = await client.connect_websocket()
    print("  WebSocket connected, waiting for notification...")

    # Send a notification
    sent = await client.send_notification(
        title="WebSocket Test",
        content="Testing real-time delivery",
        type_="success"
    )
    print(f"  Sent notification: {sent['message_id']}")

    # Wait for WebSocket message (with timeout)
    try:
        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
        data = json.loads(message)

        print(f"  Received: {data}")

        # Validate message structure
        assert data["id"] == sent["message_id"], f"ID mismatch: {data['id']} != {sent['message_id']}"
        assert data["title"] == "WebSocket Test"
        assert data["content"] == "Testing real-time delivery"
        assert data["type"] == "success"
        assert "timestamp" in data
        assert isinstance(data["read"], bool)

        print("✓ WebSocket notification received and validated")

    except asyncio.TimeoutError:
        raise AssertionError("Did not receive notification via WebSocket within 3 seconds")

    finally:
        await websocket.close()


async def test_8_multiple_notifications_websocket():
    """Test 8: Receive multiple notifications via WebSocket."""
    print("\n[TEST 8] Receive multiple notifications via WebSocket...")

    client = NotificationTestClient(TEST_USER_UUID)

    websocket = await client.connect_websocket()
    print("  WebSocket connected")

    # Send 3 notifications
    sent_ids = []
    for i in range(3):
        result = await client.send_notification(
            title=f"Batch WebSocket {i+1}",
            content=f"Message {i+1}",
            type_="info"
        )
        sent_ids.append(result["message_id"])
        await asyncio.sleep(0.2)  # Small delay between sends

    print(f"  Sent {len(sent_ids)} notifications")

    # Receive all 3 messages
    received_ids = []
    try:
        for i in range(3):
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)
            received_ids.append(data["id"])
            print(f"  Received {i+1}/3: {data['title']}")

        # Validate all received
        for sent_id in sent_ids:
            assert sent_id in received_ids, f"Missing notification {sent_id}"

        print(f"✓ All {len(received_ids)} notifications received via WebSocket")

    except asyncio.TimeoutError:
        raise AssertionError(f"Only received {len(received_ids)}/3 notifications")

    finally:
        await websocket.close()


async def test_9_notification_types():
    """Test 9: Test all notification types."""
    print("\n[TEST 9] Test all notification types...")

    client = NotificationTestClient(TEST_USER_UUID)
    types = ["info", "warning", "error", "success"]

    for notif_type in types:
        result = await client.send_notification(
            title=f"Type Test: {notif_type}",
            content=f"Testing {notif_type} type",
            type_=notif_type
        )
        assert result["status"] == "queued"
        print(f"  ✓ {notif_type}")

    print(f"✓ All {len(types)} notification types tested")


async def test_10_end_to_end_flow():
    """Test 10: Complete end-to-end flow."""
    print("\n[TEST 10] Complete end-to-end flow...")

    client = NotificationTestClient(TEST_USER_UUID)

    # 1. Connect WebSocket
    print("  1. Connecting WebSocket...")
    websocket = await client.connect_websocket()

    # 2. Send notification
    print("  2. Sending notification...")
    sent = await client.send_notification(
        title="E2E Test",
        content="End-to-end flow test",
        type_="info"
    )

    # 3. Receive via WebSocket
    print("  3. Waiting for WebSocket delivery...")
    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
    data = json.loads(message)
    assert data["id"] == sent["message_id"]
    print(f"  ✓ Received via WebSocket")

    await websocket.close()

    # 4. Verify in list
    print("  4. Verifying in notification list...")
    await asyncio.sleep(0.5)
    notifications = await client.list_notifications()
    found = any(n["id"] == sent["message_id"] for n in notifications)
    assert found, "Notification not in list"
    print(f"  ✓ Found in list")

    # 5. Check unread count
    print("  5. Checking unread count...")
    count = await client.get_unread_count()
    assert count > 0, "Should have unread notifications"
    print(f"  ✓ Unread count: {count}")

    # 6. Mark as read
    print("  6. Marking as read...")
    await client.mark_as_read(sent["message_id"])
    new_count = await client.get_unread_count()
    assert new_count < count, "Unread count should decrease"
    print(f"  ✓ Marked as read, count: {count} -> {new_count}")

    print("✓ Complete end-to-end flow successful")


# Main Test Runner

async def run_tests():
    """Run all tests in sequence."""
    tests = [
        test_1_send_notification,
        test_2_list_notifications,
        test_3_unread_count,
        test_4_mark_as_read,
        test_5_mark_all_read,
        test_6_websocket_connection,
        test_7_websocket_receive_notification,
        test_8_multiple_notifications_websocket,
        test_9_notification_types,
        test_10_end_to_end_flow,
    ]

    print("=" * 60)
    print("NOTIFICATION SYSTEM E2E TESTS")
    print("=" * 60)
    if USE_GATEWAY:
        print(f"Mode: Gateway")
    elif USE_GATEWAY_WEBSOCKET:
        print(f"Mode: Hybrid (HTTP via Backend, WebSocket via Gateway)")
    else:
        print(f"Mode: Backend Direct")
    print(f"HTTP: {GATEWAY_BASE_URL if USE_GATEWAY else BACKEND_BASE_URL}")
    print(f"WebSocket: {GATEWAY_WS_URL if USE_GATEWAY_WEBSOCKET else BACKEND_WS_URL}")
    print(f"Test User: {TEST_USER_UUID}")
    print("=" * 60)

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n✗ FAILED: {e}")
            failed += 1
            # Continue with other tests

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
