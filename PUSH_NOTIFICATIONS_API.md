# Push Notifications API Reference

Quick reference for the Push Notifications API endpoints.

**Base URL:** `/api/v1/notifications`

---

## Authentication

All endpoints require authentication via JWT token:
```
Authorization: Bearer <token>
```

---

## Endpoints

### 1. Register Device Token

Register a device for push notifications.

**Endpoint:** `POST /notifications/register`

**Request Body:**
```json
{
  "device_token": "FCM_DEVICE_TOKEN",
  "platform": "android",  // "ios", "android", or "web"
  "device_name": "My Phone"  // Optional
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "device_token": "FCM_DEVICE_TOKEN",
  "platform": "android",
  "device_name": "My Phone",
  "is_active": true,
  "created_at": "2026-01-04T10:00:00Z"
}
```

---

### 2. Unregister Device Token

Remove a device token (e.g., on logout).

**Endpoint:** `DELETE /notifications/unregister?device_token=<token>`

**Query Parameters:**
- `device_token` (required): The FCM token to unregister

**Response:** `204 No Content`

---

### 3. Get My Devices

List all registered devices for the current user.

**Endpoint:** `GET /notifications/devices?active_only=true`

**Query Parameters:**
- `active_only` (optional, default: `true`): Only return active devices

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "device_token": "FCM_TOKEN_1",
    "platform": "android",
    "device_name": "My Phone",
    "is_active": true,
    "created_at": "2026-01-04T10:00:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "device_token": "FCM_TOKEN_2",
    "platform": "ios",
    "device_name": "My iPad",
    "is_active": true,
    "created_at": "2026-01-03T15:30:00Z"
  }
]
```

---

### 4. Remove Specific Device

Remove a device by ID (useful for device management in settings).

**Endpoint:** `DELETE /notifications/devices/{device_id}`

**Path Parameters:**
- `device_id` (required): Device ID to remove

**Response:** `204 No Content`

---

### 5. Send Notification (Test/Admin)

Send a push notification to a user. For testing or admin use.

**Endpoint:** `POST /notifications/send`

**Request Body:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "notification_type": "appointment_reminder",
  "template_vars": {
    "doctor_name": "Dr. Smith",
    "appointment_time": "January 5, 2026 at 10:00 AM"
  },
  "data": {
    "appointment_id": "abc123",
    "custom_field": "value"
  }
}
```

**Notification Types:**
- `appointment_reminder`
- `appointment_confirmed`
- `appointment_cancelled`
- `appointment_rescheduled`
- `slot_offer`
- `payment_received`
- `payment_pending`
- `waitlist_position_update`
- `general_announcement`

**Response:** `200 OK`
```json
{
  "message": "Notification sent",
  "success_count": 2,
  "failed_count": 0
}
```

**Authorization:**
- Users can send to themselves
- Only admins can send to other users

---

### 6. Subscribe to Topic

Subscribe user's devices to a notification topic (e.g., clinic broadcasts).

**Endpoint:** `POST /notifications/topics/subscribe`

**Request Body:**
```json
{
  "topic": "clinic_12345"
}
```

**Response:** `200 OK`
```json
{
  "message": "Subscribed to topic 'clinic_12345'",
  "success_count": 2,
  "failed_count": 0
}
```

---

### 7. Unsubscribe from Topic

Unsubscribe from a notification topic.

**Endpoint:** `POST /notifications/topics/unsubscribe`

**Request Body:**
```json
{
  "topic": "clinic_12345"
}
```

**Response:** `200 OK`
```json
{
  "message": "Unsubscribed from topic 'clinic_12345'",
  "success_count": 2,
  "failed_count": 0
}
```

---

### 8. Test Firebase Configuration

Check if Firebase is properly configured on the backend.

**Endpoint:** `GET /notifications/test`

**Response:** `200 OK`
```json
{
  "firebase_configured": true,
  "message": "Firebase is properly configured"
}
```

Or if not configured:
```json
{
  "firebase_configured": false,
  "message": "Firebase not configured. Set FIREBASE_CREDENTIALS_PATH environment variable."
}
```

---

## Notification Template Variables

Each notification type requires specific template variables:

### appointment_reminder
```json
{
  "doctor_name": "Dr. Smith",
  "appointment_time": "January 5, 2026 at 10:00 AM"
}
```

### appointment_confirmed
```json
{
  "doctor_name": "Dr. Smith",
  "appointment_date": "January 5, 2026"
}
```

### appointment_cancelled
```json
{
  "doctor_name": "Dr. Smith",
  "appointment_date": "January 5, 2026"
}
```

### appointment_rescheduled
```json
{
  "new_appointment_time": "January 6, 2026 at 2:00 PM"
}
```

### slot_offer
```json
{
  "doctor_name": "Dr. Smith",
  "slot_time": "January 5, 2026 at 2:30 PM"
}
```

### payment_received
```json
{
  "amount": "500"
}
```

### payment_pending
```json
{
  "amount": "500",
  "appointment_date": "January 5, 2026"
}
```

### waitlist_position_update
```json
{
  "position": "5",
  "wait_time": "75 minutes"
}
```

### general_announcement
```json
{
  "title": "Clinic Closed",
  "message": "The clinic will be closed tomorrow for maintenance."
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Failed to register device: Invalid FCM token"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to send notifications to other users"
}
```

### 404 Not Found
```json
{
  "detail": "Device token not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to send notification: Firebase error"
}
```

---

## Usage Examples

### cURL Examples

**Register Device:**
```bash
curl -X POST http://localhost:8000/api/v1/notifications/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_token": "fGHJ...xyz",
    "platform": "android",
    "device_name": "My Phone"
  }'
```

**Send Test Notification:**
```bash
curl -X POST http://localhost:8000/api/v1/notifications/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "notification_type": "appointment_reminder",
    "template_vars": {
      "doctor_name": "Dr. Smith",
      "appointment_time": "Tomorrow at 10:00 AM"
    }
  }'
```

### Python Examples

**Using requests:**
```python
import requests

# Register device
response = requests.post(
    'http://localhost:8000/api/v1/notifications/register',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    },
    json={
        'device_token': 'fGHJ...xyz',
        'platform': 'android',
        'device_name': 'My Phone',
    }
)

# Send notification
response = requests.post(
    'http://localhost:8000/api/v1/notifications/send',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    },
    json={
        'user_id': '123e4567-e89b-12d3-a456-426614174000',
        'notification_type': 'appointment_reminder',
        'template_vars': {
            'doctor_name': 'Dr. Smith',
            'appointment_time': 'Tomorrow at 10:00 AM',
        }
    }
)
```

### Dart/Flutter Examples

**Register Device:**
```dart
import 'package:dio/dio.dart';

final dio = Dio();
dio.options.headers['Authorization'] = 'Bearer $token';

final response = await dio.post(
  'http://localhost:8000/api/v1/notifications/register',
  data: {
    'device_token': fcmToken,
    'platform': 'android',
    'device_name': 'My Phone',
  },
);
```

**Get My Devices:**
```dart
final response = await dio.get(
  'http://localhost:8000/api/v1/notifications/devices',
  queryParameters: {'active_only': true},
);

final devices = List<Map<String, dynamic>>.from(response.data);
```

---

## Rate Limits

Currently no rate limits are enforced, but consider implementing:

- Device registration: 10 requests per minute per user
- Notification sending: 100 requests per minute per admin
- Topic operations: 20 requests per minute per user

---

## Best Practices

1. **Register on Login:** Register device token immediately after successful authentication
2. **Unregister on Logout:** Always unregister device token when user logs out
3. **Handle Token Refresh:** Listen to FCM token refresh events and update backend
4. **Subscribe to Topics:** Auto-subscribe users to their clinic topic
5. **Error Handling:** Handle cases where Firebase is not configured gracefully
6. **Test Mode:** Use test endpoint to verify Firebase configuration before sending production notifications

---

**Last Updated:** 2026-01-04
