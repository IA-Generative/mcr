curl -X POST http://localhost:8001/api/notifications/send \
    -H "Content-Type: application/json" \
    -d '{
    "recipient_id": "f0062539-f6df-449a-adcb-a78ef5d9524f",
    "title": "Test Notification",
    "content": "Should see DsfrAlert toast!",
    "type": "success"
    }'