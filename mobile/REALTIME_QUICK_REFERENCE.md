# WebSocket Real-Time Updates - Quick Reference

## Installation

```yaml
# pubspec.yaml
dependencies:
  web_socket_channel: ^2.4.0
```

```bash
flutter pub get
```

## Import Statements

```dart
// For WebSocket service
import 'package:docassist_mobile/core/services/websocket_service.dart';

// For providers
import 'package:docassist_mobile/core/providers/realtime_provider.dart';

// For status widgets
import 'package:docassist_mobile/core/widgets/realtime_status_widget.dart';
```

## Common Use Cases

### 1. Check Connection Status

```dart
class MyWidget extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isConnected = ref.watch(isWebSocketConnectedProvider);

    return Text(isConnected ? 'Online' : 'Offline');
  }
}
```

### 2. Show Connection Status in AppBar

```dart
AppBar(
  title: Text('Dashboard'),
  actions: [
    RealtimeStatusWidget(showWhenConnected: true),
    // OR
    AppBarConnectionStatus(), // Shows only when disconnected
  ],
)
```

### 3. Listen to Specific Events

```dart
// Appointment events
ref.listen<AsyncValue<WebSocketEvent>>(
  appointmentEventsProvider,
  (previous, next) {
    next.whenData((event) {
      // Handle appointment event
      print('Appointment ${event.type}');
    });
  },
);

// Waitlist events
ref.listen<AsyncValue<WebSocketEvent>>(
  waitlistEventsProvider,
  (previous, next) {
    next.whenData((event) {
      // Handle waitlist event
    });
  },
);

// All events
ref.listen<AsyncValue<WebSocketEvent>>(
  webSocketEventsProvider,
  (previous, next) {
    next.whenData((event) {
      // Handle any event
    });
  },
);
```

### 4. Manual Reconnection

```dart
// In a button onPressed
final manager = ref.read(realtimeConnectionManagerProvider);
await manager.reconnect();

// Ensure connected (only reconnects if needed)
await manager.ensureConnected();
```

### 5. Show Connection Snackbars

```dart
// Wrap your app
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

### 6. Display Offline Badge

```dart
Stack(
  children: [
    MyContent(),
    Positioned(
      top: 8,
      right: 8,
      child: RealtimeStatusBadge(), // Shows only when offline
    ),
  ],
)
```

### 7. Get Detailed Connection State

```dart
final connectionState = ref.watch(currentConnectionStateProvider);

switch (connectionState) {
  case ConnectionState.connected:
    // Show online indicator
    break;
  case ConnectionState.connecting:
  case ConnectionState.reconnecting:
    // Show loading indicator
    break;
  case ConnectionState.disconnected:
  case ConnectionState.error:
    // Show error state
    break;
}
```

### 8. React to Connection Quality

```dart
final quality = ref.watch(connectionQualityProvider);

switch (quality) {
  case ConnectionQuality.good:
    return Icon(Icons.wifi, color: Colors.green);
  case ConnectionQuality.degraded:
    return Icon(Icons.wifi_tethering, color: Colors.orange);
  case ConnectionQuality.connecting:
    return CircularProgressIndicator();
  case ConnectionQuality.poor:
    return Icon(Icons.wifi_off, color: Colors.red);
}
```

## Event Types Reference

| Event Type | Trigger | Data Contains |
|------------|---------|---------------|
| `appointmentCreated` | New appointment booked | Full appointment object |
| `appointmentUpdated` | Appointment modified | Updated appointment object |
| `appointmentCancelled` | Appointment cancelled | Appointment ID |
| `waitlistAdded` | Patient added to waitlist | Waitlist entry object |
| `waitlistUpdated` | Waitlist entry changed | Updated entry object |
| `waitlistOfferSent` | Slot offered to patient | Offer details |
| `notification` | General notification | Notification payload |
| `heartbeat` | Keep-alive ping/pong | Empty or timestamp |

## Providers Reference

| Provider | Type | Purpose |
|----------|------|---------|
| `webSocketServiceProvider` | Provider | WebSocket service instance |
| `connectionStateProvider` | StreamProvider | Stream of connection states |
| `currentConnectionStateProvider` | Provider | Current connection state |
| `isWebSocketConnectedProvider` | Provider | Simple boolean connection status |
| `connectionQualityProvider` | Provider | Connection quality enum |
| `webSocketEventsProvider` | StreamProvider | All WebSocket events |
| `appointmentEventsProvider` | StreamProvider | Appointment events only |
| `waitlistEventsProvider` | StreamProvider | Waitlist events only |
| `notificationEventsProvider` | StreamProvider | Notification events only |
| `realtimeConnectionManagerProvider` | Provider | Connection manager |

## Widgets Reference

| Widget | Purpose | Shows When |
|--------|---------|------------|
| `RealtimeStatusWidget` | Full status with icon & text | Configurable |
| `RealtimeStatusBadge` | Compact offline badge | Disconnected only |
| `AppBarConnectionStatus` | Reconnect button | Disconnected only |
| `RealtimeConnectionSnackbar` | Auto snackbars on state change | State changes |

## Configuration

Default values (edit in `websocket_service.dart`):

```dart
static const Duration _connectionTimeout = Duration(seconds: 10);
static const Duration _heartbeatInterval = Duration(seconds: 30);
static const Duration _baseReconnectDelay = Duration(seconds: 2);
static const int _maxReconnectAttempts = 10;
```

## Debugging

Enable debug logs:

```dart
import 'package:logger/logger.dart';

Logger.level = Level.debug;
```

Check logs for:
- `[INFO] Connecting to WebSocket`
- `[INFO] WebSocket connected successfully`
- `[DEBUG] Received event: appointmentUpdated`
- `[ERROR] WebSocket connection error`

## Backend Event Format

The backend should send events in this format:

```json
{
  "type": "appointment.updated",
  "data": {
    "id": "appt_123",
    "patient_id": "pat_456",
    "status": "checked_in",
    ...
  },
  "timestamp": "2026-01-04T10:30:00Z"
}
```

## Common Pitfalls

❌ **Don't** manually call `connect()` - it's automatic on auth
✅ **Do** let the `authStateProvider` listener handle it

❌ **Don't** forget to check `isConnected` before assuming real-time data
✅ **Do** show offline indicators when disconnected

❌ **Don't** ignore connection state in UI
✅ **Do** provide feedback about connection status

❌ **Don't** implement manual polling alongside WebSocket
✅ **Do** trust the real-time updates

## Examples

### Full AppBar with Status

```dart
AppBar(
  title: Text('Appointments'),
  actions: [
    // Show status indicator
    RealtimeStatusWidget(
      showWhenConnected: true,
      padding: EdgeInsets.symmetric(horizontal: 12),
    ),

    // Reconnect button (only when disconnected)
    AppBarConnectionStatus(),

    SizedBox(width: 8),
  ],
)
```

### Event Handler with Notification

```dart
@override
void initState() {
  super.initState();

  Future.microtask(() {
    ref.listen<AsyncValue<WebSocketEvent>>(
      waitlistEventsProvider,
      (previous, next) {
        next.whenData((event) {
          if (event.type == WebSocketEventType.waitlistOfferSent) {
            // Show notification
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('New slot offer available!'),
                action: SnackBarAction(
                  label: 'View',
                  onPressed: () {
                    // Navigate to waitlist
                  },
                ),
              ),
            );
          }
        });
      },
    );
  });
}
```

### Connection-Aware Button

```dart
ElevatedButton(
  onPressed: isConnected
    ? () async {
        // Perform action that requires connection
        await submitData();
      }
    : null, // Disabled when offline
  child: Text(
    isConnected
      ? 'Submit'
      : 'Offline - Cannot Submit',
  ),
)
```

## Testing

### Mock WebSocket Service

```dart
import 'package:mocktail/mocktail.dart';

class MockWebSocketService extends Mock implements WebSocketService {}

// In test
final mockService = MockWebSocketService();
when(() => mockService.connectionState)
  .thenReturn(ConnectionState.connected);
```

### Simulate Event

```dart
final eventController = StreamController<WebSocketEvent>();

when(() => mockService.appointmentEventStream)
  .thenAnswer((_) => eventController.stream);

// Trigger event
eventController.add(WebSocketEvent(
  type: WebSocketEventType.appointmentCreated,
  data: {...},
));
```

## Help & Support

- **Full Documentation**: `lib/core/services/WEBSOCKET_README.md`
- **Implementation Summary**: `REALTIME_IMPLEMENTATION_SUMMARY.md`
- **Demo Screen**: `lib/features/realtime_demo_screen.dart`

---

**Version**: 1.0.0
**Last Updated**: 2026-01-04
