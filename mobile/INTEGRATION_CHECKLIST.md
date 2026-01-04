# WebSocket Integration Checklist

## Phase 1: Setup ✓

- [x] Add `web_socket_channel: ^2.4.0` to `pubspec.yaml`
- [x] Create WebSocket service (`lib/core/services/websocket_service.dart`)
- [x] Create Riverpod providers (`lib/core/providers/realtime_provider.dart`)
- [x] Create status widgets (`lib/core/widgets/realtime_status_widget.dart`)
- [x] Update appointments provider for real-time updates
- [x] Update waitlist provider for real-time updates
- [x] Add generic HTTP methods to API client
- [x] Create demo screen (`lib/features/realtime_demo_screen.dart`)
- [x] Create documentation

## Phase 2: Mobile App Integration

### Step 1: Install Dependencies
```bash
cd /home/user/appointment_system/mobile
flutter pub get
```

### Step 2: Test Compilation
```bash
flutter analyze
```
Expected: No errors related to WebSocket implementation

### Step 3: Update Main App
Add connection status snackbar wrapper to `lib/main.dart`:

```dart
import 'core/widgets/realtime_status_widget.dart';

void main() {
  runApp(
    ProviderScope(
      child: RealtimeConnectionSnackbar(
        child: MyApp(),
      ),
    ),
  );
}
```

### Step 4: Add Status to AppBar
Update your main screens (Dashboard, Appointments, etc.):

```dart
AppBar(
  title: Text('Appointments'),
  actions: [
    RealtimeStatusWidget(showWhenConnected: true),
    AppBarConnectionStatus(),
    SizedBox(width: 8),
  ],
)
```

### Step 5: Test Real-Time Updates
1. Login to the app
2. Check logs for WebSocket connection
3. Create/update appointment from another client
4. Verify app updates automatically

### Step 6: Add Demo Screen (Optional)
Add route to `lib/config/router.dart`:

```dart
GoRoute(
  path: '/realtime-demo',
  builder: (context, state) => RealtimeDemoScreen(),
)
```

## Phase 3: Backend Implementation

### Step 1: Install Dependencies
```bash
cd /home/user/appointment_system/backend
pip install websockets
```

### Step 2: Create WebSocket Manager
Create `backend/app/websocket/manager.py`:

```python
from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()
```

### Step 3: Create WebSocket Endpoint
Add to `backend/app/api/v1/websocket.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime
from ...auth.jwt import verify_token
from .websocket.manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
):
    # Authenticate
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Connect
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()

            # Handle heartbeat
            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)
```

### Step 4: Add WebSocket Router to Main App
Update `backend/app/main.py`:

```python
from app.api.v1 import websocket

app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
```

### Step 5: Broadcast Events
Add broadcasting to appointment/waitlist services:

```python
from app.api.v1.websocket.manager import manager

# After creating/updating appointment
await manager.broadcast({
    "type": "appointment.updated",
    "data": appointment.dict(),
    "timestamp": datetime.utcnow().isoformat()
})

# After waitlist update
await manager.broadcast({
    "type": "waitlist.updated",
    "data": waitlist_entry.dict(),
    "timestamp": datetime.utcnow().isoformat()
})
```

### Step 6: Test Backend
```bash
# Start server
uvicorn app.main:app --reload

# Check WebSocket endpoint
# Use browser console or wscat
wscat -c "ws://localhost:8000/api/v1/ws?token=YOUR_JWT_TOKEN"
```

## Phase 4: Testing

### Manual Testing
- [ ] User can login successfully
- [ ] WebSocket connects automatically after login
- [ ] Status indicator shows "Connected"
- [ ] Create appointment → UI updates in real-time
- [ ] Update appointment → UI updates in real-time
- [ ] Cancel appointment → UI updates in real-time
- [ ] Add to waitlist → UI updates in real-time
- [ ] Update waitlist → UI updates in real-time
- [ ] Logout → WebSocket disconnects
- [ ] Login again → WebSocket reconnects
- [ ] Put app in background → Connection stays alive
- [ ] Resume app → Reconnects if needed
- [ ] Turn off WiFi → Shows "Reconnecting..."
- [ ] Turn on WiFi → Reconnects automatically
- [ ] Multiple reconnection attempts work correctly
- [ ] Max reconnection attempts respected

### Connection Testing
- [ ] Connection timeout works (10 seconds)
- [ ] Heartbeat keeps connection alive (30 seconds)
- [ ] Reconnection backoff is exponential (2s, 4s, 8s, 16s, 32s, 60s)
- [ ] Max 10 reconnection attempts before giving up
- [ ] Connection state updates correctly
- [ ] Connection snackbars show appropriately

### Event Testing
- [ ] Appointment events route to correct stream
- [ ] Waitlist events route to correct stream
- [ ] Notification events route to correct stream
- [ ] Heartbeat events don't trigger updates
- [ ] Unknown events are logged but don't crash
- [ ] Malformed JSON doesn't crash the app

### UI Testing
- [ ] Status widget shows correct color (green/orange/red)
- [ ] Status badge hides when connected
- [ ] AppBar button shows only when disconnected
- [ ] Reconnect button triggers reconnection
- [ ] Demo screen displays events correctly
- [ ] Event details modal works

### Performance Testing
- [ ] Memory usage is acceptable (<500KB overhead)
- [ ] CPU usage is minimal during idle
- [ ] Battery drain is negligible
- [ ] Network usage is reasonable
- [ ] No memory leaks after extended use

### Error Testing
- [ ] Invalid JWT token rejected
- [ ] Backend down → Shows error state
- [ ] Backend restart → Auto-reconnects
- [ ] Network interruption → Reconnects
- [ ] Malformed events → Logged, not crashed
- [ ] Stream errors → Handled gracefully

## Phase 5: Deployment

### Pre-deployment Checklist
- [ ] All tests passing
- [ ] No console errors
- [ ] Documentation complete
- [ ] Backend WebSocket endpoint deployed
- [ ] SSL/TLS configured (wss:// for production)
- [ ] Load balancer configured for WebSocket
- [ ] Monitoring/logging in place

### Production Configuration
- [ ] WebSocket URL points to production server
- [ ] Heartbeat interval optimized
- [ ] Reconnection strategy tuned
- [ ] Error logging configured
- [ ] Analytics tracking added (optional)

### Monitoring
- [ ] Track connection success rate
- [ ] Monitor reconnection attempts
- [ ] Log WebSocket errors
- [ ] Track event throughput
- [ ] Monitor memory/CPU usage

## Troubleshooting Guide

### Issue: WebSocket won't connect
**Check:**
- Backend is running
- WebSocket endpoint exists at `/api/v1/ws`
- JWT token is valid
- Network connectivity
- Firewall/proxy settings

**Solution:**
```dart
final manager = ref.read(realtimeConnectionManagerProvider);
await manager.reconnect();
```

### Issue: Events not received
**Check:**
- Connection state is "connected"
- Backend is sending events
- Event format matches expected structure
- Event type is recognized

**Solution:**
- Check logs for parsing errors
- Verify event type matches enum values
- Ensure backend sends correct format

### Issue: High battery drain
**Check:**
- Heartbeat interval (default 30s)
- Reconnection frequency
- Event volume

**Solution:**
- Increase heartbeat interval
- Disconnect when app paused
- Implement event filtering

### Issue: Connection keeps dropping
**Check:**
- Network stability
- Backend timeout settings
- Load balancer configuration
- Heartbeat response

**Solution:**
- Adjust heartbeat interval
- Check backend configuration
- Review load balancer WebSocket support

## Success Criteria

✅ WebSocket connects on login
✅ Auto-reconnects after network interruption
✅ UI updates in real-time
✅ No manual polling required
✅ Graceful degradation when offline
✅ Clear user feedback on connection status
✅ No performance impact
✅ Production-ready error handling

## Support Resources

- **Full Documentation**: `lib/core/services/WEBSOCKET_README.md`
- **Quick Reference**: `REALTIME_QUICK_REFERENCE.md`
- **Implementation Summary**: `REALTIME_IMPLEMENTATION_SUMMARY.md`
- **Demo Screen**: `lib/features/realtime_demo_screen.dart`

## Next Steps After Integration

1. Monitor production metrics
2. Gather user feedback
3. Optimize based on usage patterns
4. Consider advanced features:
   - Push notifications integration
   - Offline message queue
   - Message compression
   - Binary protocol
   - Custom event filters

---

**Status**: Ready for integration
**Version**: 1.0.0
**Date**: 2026-01-04
