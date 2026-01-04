# WebSocket Client Examples

This document provides examples for connecting to the DocAssist Practice Manager WebSocket API from various client platforms.

## Connection Details

- **Endpoint**: `ws://localhost:8000/api/v1/ws` (development) or `wss://your-domain.com/api/v1/ws` (production)
- **Authentication**: JWT token in query parameter
- **Required Parameters**:
  - `token`: JWT access token from login
  - `clinic_id`: Clinic UUID to subscribe to

## Message Format

### Incoming Messages (Server → Client)

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

### Outgoing Messages (Client → Server)

```json
{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Event Types

### Appointment Events
- `appointment_created`: New appointment scheduled
- `appointment_updated`: Appointment details changed
- `appointment_cancelled`: Appointment cancelled
- `appointment_confirmed`: Patient confirmed attendance
- `appointment_checked_in`: Patient checked in at clinic
- `appointment_started`: Consultation started
- `appointment_completed`: Consultation completed
- `appointment_no_show`: Patient did not show up

### Waitlist Events
- `waitlist_joined`: Patient added to waitlist
- `waitlist_updated`: Waitlist entry updated
- `waitlist_slot_available`: Slot became available for patient
- `waitlist_booked`: Waitlist entry converted to appointment
- `waitlist_expired`: Waitlist entry expired
- `waitlist_cancelled`: Patient cancelled waitlist entry

### Notification Events
- `notification_new`: New notification
- `notification_reminder`: Reminder notification
- `notification_alert`: Alert notification

### System Events
- `ping`: Heartbeat from server
- `connected`: Connection established
- `system_maintenance`: System maintenance announcement
- `system_update`: System update notification

---

## JavaScript/TypeScript Example

```typescript
class DocAssistWebSocket {
  private ws: WebSocket | null = null;
  private token: string;
  private clinicId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(token: string, clinicId: string) {
    this.token = token;
    this.clinicId = clinicId;
  }

  connect(): void {
    const wsUrl = `ws://localhost:8000/api/v1/ws?token=${this.token}&clinic_id=${this.clinicId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };
  }

  private handleMessage(message: any): void {
    switch (message.event_type) {
      case 'ping':
        // Respond to heartbeat
        this.sendPong();
        break;

      case 'connected':
        console.log('Connection confirmed:', message.data);
        break;

      case 'appointment_created':
        this.onAppointmentCreated(message.data);
        break;

      case 'appointment_updated':
        this.onAppointmentUpdated(message.data);
        break;

      case 'waitlist_slot_available':
        this.onWaitlistSlotAvailable(message.data);
        break;

      case 'notification_new':
        this.onNotification(message.data);
        break;

      default:
        console.log('Unhandled event:', message.event_type, message);
    }
  }

  private sendPong(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'pong',
        timestamp: new Date().toISOString(),
      }));
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => this.connect(), delay);
    }
  }

  // Event handlers (implement these based on your UI)
  private onAppointmentCreated(data: any): void {
    console.log('New appointment:', data);
    // Update UI, show notification, etc.
  }

  private onAppointmentUpdated(data: any): void {
    console.log('Appointment updated:', data);
    // Update appointment in UI
  }

  private onWaitlistSlotAvailable(data: any): void {
    console.log('Waitlist slot available:', data);
    // Show alert to user
  }

  private onNotification(data: any): void {
    console.log('New notification:', data);
    // Show notification toast
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Usage
const token = 'your-jwt-token';
const clinicId = '550e8400-e29b-41d4-a716-446655440000';
const wsClient = new DocAssistWebSocket(token, clinicId);
wsClient.connect();
```

---

## Flutter/Dart Example

```dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class DocAssistWebSocket {
  WebSocketChannel? _channel;
  final String token;
  final String clinicId;
  int _reconnectAttempts = 0;
  final int _maxReconnectAttempts = 5;
  Timer? _reconnectTimer;

  // Event controllers
  final StreamController<Map<String, dynamic>> _appointmentController =
      StreamController.broadcast();
  final StreamController<Map<String, dynamic>> _waitlistController =
      StreamController.broadcast();
  final StreamController<Map<String, dynamic>> _notificationController =
      StreamController.broadcast();

  // Event streams
  Stream<Map<String, dynamic>> get appointmentStream =>
      _appointmentController.stream;
  Stream<Map<String, dynamic>> get waitlistStream =>
      _waitlistController.stream;
  Stream<Map<String, dynamic>> get notificationStream =>
      _notificationController.stream;

  DocAssistWebSocket({
    required this.token,
    required this.clinicId,
  });

  void connect() {
    final wsUrl = Uri.parse(
      'ws://localhost:8000/api/v1/ws?token=$token&clinic_id=$clinicId',
    );

    _channel = WebSocketChannel.connect(wsUrl);

    _channel!.stream.listen(
      (message) {
        final data = jsonDecode(message as String) as Map<String, dynamic>;
        _handleMessage(data);
      },
      onError: (error) {
        print('WebSocket error: $error');
      },
      onDone: () {
        print('WebSocket disconnected');
        _attemptReconnect();
      },
    );

    print('WebSocket connected');
    _reconnectAttempts = 0;
  }

  void _handleMessage(Map<String, dynamic> message) {
    final eventType = message['event_type'] as String;

    switch (eventType) {
      case 'ping':
        _sendPong();
        break;

      case 'connected':
        print('Connection confirmed: ${message['data']}');
        break;

      case 'appointment_created':
      case 'appointment_updated':
      case 'appointment_cancelled':
      case 'appointment_confirmed':
      case 'appointment_checked_in':
      case 'appointment_started':
      case 'appointment_completed':
      case 'appointment_no_show':
        _appointmentController.add(message);
        break;

      case 'waitlist_joined':
      case 'waitlist_updated':
      case 'waitlist_slot_available':
      case 'waitlist_booked':
      case 'waitlist_expired':
      case 'waitlist_cancelled':
        _waitlistController.add(message);
        break;

      case 'notification_new':
      case 'notification_reminder':
      case 'notification_alert':
        _notificationController.add(message);
        break;

      default:
        print('Unhandled event: $eventType');
    }
  }

  void _sendPong() {
    if (_channel != null) {
      _channel!.sink.add(jsonEncode({
        'type': 'pong',
        'timestamp': DateTime.now().toIso8601String(),
      }));
    }
  }

  void _attemptReconnect() {
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectAttempts++;
      final delay = Duration(
        milliseconds: (1000 * (1 << _reconnectAttempts)).clamp(0, 30000),
      );

      print('Reconnecting in ${delay.inSeconds}s '
          '(attempt $_reconnectAttempts/$_maxReconnectAttempts)');

      _reconnectTimer = Timer(delay, connect);
    }
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    disconnect();
    _appointmentController.close();
    _waitlistController.close();
    _notificationController.close();
  }
}

// Usage in a Flutter widget
class AppointmentScreen extends StatefulWidget {
  @override
  _AppointmentScreenState createState() => _AppointmentScreenState();
}

class _AppointmentScreenState extends State<AppointmentScreen> {
  late DocAssistWebSocket _wsClient;
  StreamSubscription? _appointmentSubscription;

  @override
  void initState() {
    super.initState();

    final token = 'your-jwt-token';
    final clinicId = '550e8400-e29b-41d4-a716-446655440000';

    _wsClient = DocAssistWebSocket(token: token, clinicId: clinicId);
    _wsClient.connect();

    // Listen to appointment events
    _appointmentSubscription = _wsClient.appointmentStream.listen((event) {
      final eventType = event['event_type'] as String;
      final data = event['data'] as Map<String, dynamic>;

      switch (eventType) {
        case 'appointment_created':
          _showNotification('New appointment scheduled');
          _refreshAppointmentList();
          break;

        case 'appointment_updated':
          _updateAppointment(data);
          break;

        case 'appointment_cancelled':
          _showNotification('Appointment cancelled');
          _refreshAppointmentList();
          break;
      }
    });
  }

  void _showNotification(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _refreshAppointmentList() {
    // Refresh appointment list
    setState(() {
      // Update your state
    });
  }

  void _updateAppointment(Map<String, dynamic> data) {
    // Update specific appointment
    setState(() {
      // Update your state
    });
  }

  @override
  void dispose() {
    _appointmentSubscription?.cancel();
    _wsClient.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Your widget build method
    return Container();
  }
}
```

---

## Python Example (for testing)

```python
import asyncio
import json
import websockets


async def test_websocket():
    """Test WebSocket connection."""
    token = "your-jwt-token"
    clinic_id = "550e8400-e29b-41d4-a716-446655440000"

    uri = f"ws://localhost:8000/api/v1/ws?token={token}&clinic_id={clinic_id}"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            event_type = data.get("event_type")

            print(f"Received event: {event_type}")
            print(f"Data: {json.dumps(data, indent=2)}")

            # Respond to ping
            if event_type == "ping":
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": "2024-01-01T12:00:00"
                }))


if __name__ == "__main__":
    asyncio.run(test_websocket())
```

---

## Testing with WebSocket Tools

### Using websocat (CLI tool)

```bash
# Install websocat
# brew install websocat  # macOS
# or download from: https://github.com/vi/websocat

# Connect to WebSocket
websocat "ws://localhost:8000/api/v1/ws?token=YOUR_JWT_TOKEN&clinic_id=CLINIC_UUID"
```

### Using Browser DevTools

```javascript
// Open browser console and run:
const token = "your-jwt-token";
const clinicId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws?token=${token}&clinic_id=${clinicId}`);

ws.onopen = () => console.log("Connected");
ws.onmessage = (event) => console.log("Message:", JSON.parse(event.data));
ws.onerror = (error) => console.error("Error:", error);
ws.onclose = () => console.log("Disconnected");
```

---

## Best Practices

1. **Token Refresh**: Monitor token expiration and reconnect with a new token before expiration
2. **Reconnection**: Implement exponential backoff for reconnection attempts
3. **Heartbeat**: Respond to `ping` events with `pong` to keep connection alive
4. **Error Handling**: Handle disconnections gracefully and notify users
5. **Event Filtering**: Only subscribe to events relevant to the current view
6. **State Management**: Update local state based on received events
7. **Notifications**: Show user-friendly notifications for important events
8. **Security**: Never log or expose JWT tokens in production

---

## Troubleshooting

### Connection Refused
- Check if backend server is running
- Verify the WebSocket endpoint URL
- Ensure firewall allows WebSocket connections

### Authentication Failed (1008 error)
- Verify JWT token is valid and not expired
- Check token format in query parameter
- Ensure user has access to the specified clinic

### Connection Drops Frequently
- Check network stability
- Verify heartbeat/ping-pong is working
- Check server logs for errors
- Consider increasing timeout values

### Events Not Received
- Verify clinic_id matches your subscription
- Check event publishing in backend services
- Ensure connection manager is initialized
- Check server logs for event publishing

---

## Next Steps

1. Integrate WebSocket client into your Flutter app
2. Add event handlers for each event type
3. Update UI in response to real-time events
4. Test with multiple simultaneous connections
5. Implement proper error handling and reconnection logic
6. Add loading states and offline indicators
