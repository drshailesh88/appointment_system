# WebSocket Real-Time Updates Implementation

## Overview

This document describes the WebSocket backend implementation for real-time updates in the DocAssist Practice Manager. The system provides real-time notifications for appointments, waitlist changes, and general system events.

## Architecture

### Components

1. **WebSocket Endpoint** (`app/api/v1/websocket.py`)
   - Handles WebSocket connections
   - Manages authentication via JWT
   - Implements heartbeat/ping-pong
   - Organizes connections by clinic (room-based)

2. **Realtime Service** (`app/services/realtime.py`)
   - Publishes events to connected clients
   - Provides typed event schemas
   - Integration layer for existing services

3. **Connection Manager**
   - Manages active WebSocket connections
   - Handles broadcasting to clinics or all clients
   - Implements graceful disconnection

## Features

### Authentication
- JWT token-based authentication via query parameters
- Token validation on connection
- User and clinic verification

### Connection Management
- Multiple connections per user supported
- Room-based subscriptions by clinic_id
- Automatic heartbeat every 30 seconds
- Graceful disconnection handling
- Automatic reconnection support (client-side)

### Event Broadcasting
- Broadcast to specific clinic (room)
- Broadcast to specific user
- Broadcast to all connected clients
- Non-blocking async message delivery

### Event Types

#### Appointment Events
- `appointment_created`: New appointment scheduled
- `appointment_updated`: Appointment details changed
- `appointment_cancelled`: Appointment cancelled
- `appointment_confirmed`: Patient confirmed
- `appointment_checked_in`: Patient checked in
- `appointment_started`: Consultation started
- `appointment_completed`: Consultation completed
- `appointment_no_show`: Patient no-show

#### Waitlist Events
- `waitlist_joined`: Patient added to waitlist
- `waitlist_updated`: Waitlist entry updated
- `waitlist_slot_available`: Slot available for patient
- `waitlist_booked`: Waitlist converted to appointment
- `waitlist_expired`: Waitlist entry expired
- `waitlist_cancelled`: Patient cancelled

#### Notification Events
- `notification_new`: New notification
- `notification_reminder`: Reminder notification
- `notification_alert`: Alert notification

#### System Events
- `ping`: Heartbeat from server
- `connected`: Connection established
- `system_maintenance`: Maintenance announcement
- `system_update`: System update notification

## Files Created

### Core Implementation

1. **`/home/user/appointment_system/backend/app/api/v1/websocket.py`**
   - WebSocket router and endpoint
   - ConnectionManager class
   - Authentication logic
   - Heartbeat implementation

2. **`/home/user/appointment_system/backend/app/services/realtime.py`**
   - RealtimeService class
   - Event type definitions
   - Event payload schemas
   - Publishing methods

3. **`/home/user/appointment_system/backend/app/main.py`** (updated)
   - Initialize realtime service on startup
   - Wire connection manager to service

4. **`/home/user/appointment_system/backend/app/api/v1/__init__.py`** (updated)
   - Include WebSocket router

5. **`/home/user/appointment_system/backend/app/core/config.py`** (updated)
   - Add cors_origins and version properties

### Documentation

6. **`/home/user/appointment_system/backend/docs/websocket_client_examples.md`**
   - Client connection examples (JavaScript, Flutter, Python)
   - Message format documentation
   - Troubleshooting guide

7. **`/home/user/appointment_system/backend/app/services/realtime_integration_example.py`**
   - Integration examples for existing services
   - Code snippets for common use cases

## Usage

### Starting the Server

The WebSocket service is automatically initialized when the FastAPI server starts:

```bash
cd /home/user/appointment_system/backend
uvicorn app.main:app --reload
```

The WebSocket endpoint will be available at: `ws://localhost:8000/api/v1/ws`

### Connecting to WebSocket

Clients must provide:
- `token`: JWT access token (from login)
- `clinic_id`: Clinic UUID to subscribe to

Example URL:
```
ws://localhost:8000/api/v1/ws?token=YOUR_JWT_TOKEN&clinic_id=CLINIC_UUID
```

### Publishing Events from Services

Example: Publishing an appointment created event

```python
from app.services.realtime import (
    AppointmentEventData,
    EventType,
    get_realtime_service,
)

# In your appointment creation endpoint
async def create_appointment(...):
    # ... create appointment logic ...

    # Publish real-time event
    realtime = get_realtime_service()
    appointment_data = AppointmentEventData(
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        patient_name=appointment.patient.name,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor.name,
        scheduled_start=appointment.scheduled_start,
        scheduled_end=appointment.scheduled_end,
        status=appointment.status,
        token_number=appointment.token_number,
        chief_complaint=appointment.chief_complaint,
    )

    await realtime.publish_appointment_event(
        event_type=EventType.APPOINTMENT_CREATED,
        clinic_id=current_user.clinic_id,
        appointment_data=appointment_data,
        metadata={"created_by": str(current_user.id)},
    )
```

## Integration Guide

### Step 1: Import the Realtime Service

```python
from app.services.realtime import get_realtime_service, EventType, AppointmentEventData
```

### Step 2: Get Service Instance

```python
realtime = get_realtime_service()
```

### Step 3: Create Event Data

```python
event_data = AppointmentEventData(
    appointment_id=appointment.id,
    # ... other fields
)
```

### Step 4: Publish Event

```python
await realtime.publish_appointment_event(
    event_type=EventType.APPOINTMENT_CREATED,
    clinic_id=clinic_id,
    appointment_data=event_data,
)
```

## Message Format

### Outgoing (Server → Client)

```json
{
  "event_type": "appointment_created",
  "timestamp": "2024-01-01T12:00:00",
  "clinic_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "appointment_id": "660e8400-e29b-41d4-a716-446655440000",
    "patient_name": "John Doe",
    "doctor_name": "Dr. Smith",
    "scheduled_start": "2024-01-02T10:00:00",
    "status": "scheduled"
  },
  "metadata": {
    "created_by": "user_id"
  }
}
```

### Incoming (Client → Server)

```json
{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Error Handling

### Connection Errors

- **1008**: Authentication failed (invalid token, missing permissions)
- **1000**: Normal closure
- **1001**: Going away (server shutdown)

### Disconnection Handling

The connection manager automatically:
1. Removes disconnected clients from active connections
2. Cancels heartbeat tasks
3. Cleans up empty clinic rooms
4. Logs disconnection events

## Testing

### Manual Testing with Browser

```javascript
const token = "your-jwt-token";
const clinicId = "your-clinic-id";
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws?token=${token}&clinic_id=${clinicId}`);

ws.onopen = () => console.log("Connected");
ws.onmessage = (event) => console.log("Message:", JSON.parse(event.data));
ws.onerror = (error) => console.error("Error:", error);
ws.onclose = () => console.log("Disconnected");
```

### Testing with Python

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = f"ws://localhost:8000/api/v1/ws?token={token}&clinic_id={clinic_id}"
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['event_type']}")

            # Respond to ping
            if data['event_type'] == 'ping':
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": "2024-01-01T12:00:00"
                }))

asyncio.run(test_websocket())
```

## Performance Considerations

### Scalability
- Connections organized by clinic for efficient broadcasting
- Non-blocking async message delivery
- Connection pooling for multiple users

### Resource Management
- Automatic cleanup of disconnected clients
- Heartbeat tasks to detect dead connections
- Thread-safe connection management with asyncio.Lock

### Network Efficiency
- JSON message format (lightweight)
- Heartbeat every 30 seconds (configurable)
- Event-driven updates (no polling)

## Security

### Authentication
- JWT token validation on connect
- Token type verification (access tokens only)
- User active status check

### Authorization
- Clinic-based access control
- Users only receive events for their clinic
- Admin users can access multiple clinics

### Best Practices
- Always use WSS (WebSocket Secure) in production
- Rotate JWT tokens before expiration
- Implement rate limiting for connections
- Monitor for connection abuse

## Monitoring

### Metrics to Track
- Active connection count per clinic
- Message throughput
- Connection/disconnection rate
- Failed authentication attempts
- Average message latency

### Logging
The implementation logs:
- Connection/disconnection events
- Authentication failures
- Message delivery errors
- Heartbeat failures

## Next Steps

### Phase 7 Implementation Tasks

1. **Integrate with Existing Services**
   - [ ] Add event publishing to appointment endpoints
   - [ ] Add event publishing to waitlist service
   - [ ] Add event publishing to notification system

2. **Mobile App Integration**
   - [ ] Implement WebSocket client in Flutter
   - [ ] Add event handlers for UI updates
   - [ ] Implement reconnection logic
   - [ ] Add offline state handling

3. **Testing**
   - [ ] Write integration tests
   - [ ] Test with multiple simultaneous connections
   - [ ] Load testing for scalability
   - [ ] Test reconnection scenarios

4. **Production Readiness**
   - [ ] Configure WSS with SSL certificates
   - [ ] Set up connection monitoring
   - [ ] Implement rate limiting
   - [ ] Add connection metrics to analytics

## Troubleshooting

### Common Issues

**Connection Refused**
- Check if server is running
- Verify WebSocket endpoint URL
- Check firewall settings

**Authentication Failed**
- Verify JWT token is valid
- Check token expiration
- Ensure user has clinic access

**Events Not Received**
- Verify clinic_id matches subscription
- Check event publishing in backend
- Ensure connection manager is initialized

**Frequent Disconnections**
- Check network stability
- Verify heartbeat is working
- Check server logs for errors

## References

- [FastAPI WebSockets Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Protocol RFC 6455](https://tools.ietf.org/html/rfc6455)
- [Client Examples](/home/user/appointment_system/backend/docs/websocket_client_examples.md)
- [Integration Examples](/home/user/appointment_system/backend/app/services/realtime_integration_example.py)

---

**Last Updated**: 2026-01-04
**Author**: Claude Code
**Version**: 1.0.0
