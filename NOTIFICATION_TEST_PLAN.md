# Notification System Integration Test Plan

## Test Objectives
Validate the complete notification flow from publishing through NATS to WebSocket delivery.

## System Under Test
- **Backend**: localhost:8001 (mcr-core/mcr_meeting)
- **Gateway**: localhost:8000 (mcr-gateway)
- **NATS**: nats://localhost:4222
- **Test User**: fake@fake.com (keycloak_uuid: f0062539-f6df-449a-adcb-a78ef5d9524f)

---

## Test Categories

### 1. HTTP API Tests (via Backend :8001)

#### 1.1 Send Notification
- **Endpoint**: POST /api/notifications/send
- **Test**: Successfully publish notification to NATS
- **Assertions**:
  - Returns 202 status
  - Response contains: status="queued", message_id, recipient_id
  - Message_id is valid UUID

#### 1.2 List Notifications (Empty State)
- **Endpoint**: GET /api/notifications
- **Test**: Fetch notifications when none exist in store
- **Assertions**:
  - Returns 200 status
  - Response is empty array []

#### 1.3 List Notifications (With Data)
- **Setup**: Send notification first
- **Endpoint**: GET /api/notifications?limit=10&offset=0
- **Assertions**:
  - Returns 200 status
  - Response contains notification with correct structure
  - Fields present: id, title, content, type, read, timestamp
  - Notification matches sent data

#### 1.4 Get Unread Count
- **Endpoint**: GET /api/notifications/unread/count
- **Assertions**:
  - Returns 200 status
  - Response format: {"count": <number>}
  - Count increments after sending notification
  - Count decrements after marking as read

#### 1.5 Mark Notification as Read
- **Setup**: Send notification, get its ID
- **Endpoint**: PATCH /api/notifications/{id}
- **Assertions**:
  - Returns 200 status
  - Notification read field changes to true
  - Unread count decreases

#### 1.6 Mark All as Read
- **Setup**: Send multiple notifications
- **Endpoint**: POST /api/notifications/mark-all-read
- **Assertions**:
  - Returns 200 status
  - All notifications have read=true
  - Unread count becomes 0

#### 1.7 Authentication Required
- **Test**: Call endpoints without X-User-Keycloak-Uuid header
- **Assertions**:
  - Returns 422 (validation error) or 401 (unauthorized)

---

### 2. Gateway Proxy Tests (via Gateway :8000)

#### 2.1 Gateway - Send Notification
- **Endpoint**: POST localhost:8000/api/notifications/send
- **Test**: Gateway correctly proxies to backend
- **Assertions**:
  - Same behavior as 1.1 but through gateway
  - Authentication required

#### 2.2 Gateway - List Notifications
- **Endpoint**: GET localhost:8000/api/notifications
- **Test**: Gateway correctly proxies to backend
- **Assertions**:
  - Same behavior as 1.2/1.3 but through gateway

#### 2.3 Gateway - No 307 Redirects
- **Test**: Verify trailing slash handling is fixed
- **Assertions**:
  - GET /api/notifications/ doesn't return 307
  - GET /api/notifications returns 200 (or 401 if no auth)

---

### 3. WebSocket Tests

#### 3.1 WebSocket Connection
- **Endpoint**: ws://localhost:8001/api/notifications/ws?token={jwt}
- **Test**: Successfully establish WebSocket connection
- **Assertions**:
  - Connection accepted (101 status)
  - No immediate disconnect
  - Connection stays open

#### 3.2 WebSocket - Receive Notification
- **Setup**:
  1. Connect WebSocket
  2. Send notification via HTTP POST
- **Test**: Notification is delivered through WebSocket
- **Assertions**:
  - WebSocket receives message within reasonable time (< 2 seconds)
  - Message structure matches NotificationResponse schema
  - Message contains: id, title, content, type, read, timestamp
  - Data matches sent notification

#### 3.3 WebSocket - Multiple Notifications
- **Setup**: Connect WebSocket
- **Test**: Send 3 notifications in sequence
- **Assertions**:
  - All 3 notifications received via WebSocket
  - Order is preserved
  - Each has unique ID

#### 3.4 WebSocket - User Isolation
- **Setup**: Connect as user A, send notification to user B
- **Test**: User A should NOT receive user B's notification
- **Assertions**:
  - WebSocket connected as user A receives no message
  - Only targeted user receives notification

#### 3.5 WebSocket Reconnection
- **Test**: Disconnect and reconnect WebSocket
- **Assertions**:
  - Can reconnect successfully
  - Previous messages not re-delivered
  - New messages delivered correctly

---

### 4. NATS Integration Tests

#### 4.1 NATS Stream Exists
- **Test**: Verify NOTIF stream is created
- **Assertions**:
  - Stream "NOTIF" exists
  - Subject pattern is "NOTIF.>"
  - Consumer "mcr-consumer" exists

#### 4.2 NATS Message Publishing
- **Test**: Published notifications appear in NATS
- **Assertions**:
  - Message published to correct subject: NOTIF.notifications.{user_id}
  - Message contains all required fields
  - Message acknowledged by stream

#### 4.3 NATS Consumer Processing
- **Test**: Consumer picks up messages from stream
- **Assertions**:
  - Consumer processes messages
  - Message appears in backend notification store
  - Broadcast callback triggered

---

### 5. End-to-End Flow Tests

#### 5.1 Complete Notification Flow
- **Steps**:
  1. Start WebSocket connection for user
  2. Send notification via HTTP POST
  3. Wait for WebSocket message
  4. Verify notification in GET list
  5. Mark as read
  6. Verify unread count updated
- **Assertions**: All steps succeed in sequence

#### 5.2 Multiple Concurrent Users
- **Setup**: 2 WebSocket connections (user A, user B)
- **Test**: Send notifications to both users
- **Assertions**:
  - User A receives only their notifications
  - User B receives only their notifications
  - No cross-contamination

#### 5.3 Notification Types
- **Test**: Send all notification types: info, warning, error, success
- **Assertions**:
  - All types accepted and delivered
  - Type field preserved correctly

---

## Test Implementation Strategy

### Approach 1: Python Integration Test Script
```python
# test_notifications.py
- Use httpx for HTTP requests
- Use websockets library for WebSocket
- Use asyncio for concurrent operations
- Single script with multiple test functions
```

### Approach 2: Shell Script + Python Hybrid
```bash
# test_notifications.sh
- Basic HTTP tests with curl
- Call Python for WebSocket tests
- Use jq for JSON assertions
```

### Approach 3: pytest Test Suite
```python
# tests/integration/test_notifications.py
- pytest fixtures for setup
- Separate test functions
- Better reporting and isolation
```

## Test Data

### Valid User
- UUID: f0062539-f6df-449a-adcb-a78ef5d9524f
- Email: fake@fake.com

### Sample Notifications
```json
{
  "recipient_id": "f0062539-f6df-449a-adcb-a78ef5d9524f",
  "title": "Test Notification",
  "content": "This is a test notification",
  "type": "info",
  "link": null
}
```

## Success Criteria

- All API endpoints return expected status codes
- Notifications flow through NATS correctly
- WebSocket receives real-time notifications
- User isolation works (no cross-user leaks)
- Read/unread state management works
- Gateway proxying functions correctly
- No 307 redirects or routing errors

## Test Execution Order

1. Verify NATS connection and stream setup
2. Test HTTP API endpoints (backend)
3. Test Gateway proxy functionality
4. Test WebSocket connection and delivery
5. Test end-to-end flow
6. Test edge cases and error conditions
