import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../core/providers/realtime_provider.dart';
import '../core/services/websocket_service.dart';
import '../core/widgets/realtime_status_widget.dart';

/// Demo screen showing real-time WebSocket features
/// This is an example implementation - can be removed in production
class RealtimeDemoScreen extends ConsumerStatefulWidget {
  const RealtimeDemoScreen({super.key});

  @override
  ConsumerState<RealtimeDemoScreen> createState() => _RealtimeDemoScreenState();
}

class _RealtimeDemoScreenState extends ConsumerState<RealtimeDemoScreen> {
  final List<WebSocketEvent> _recentEvents = [];
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Listen to all events for demo purposes
    Future.microtask(() {
      ref.listen<AsyncValue<WebSocketEvent>>(
        webSocketEventsProvider,
        (previous, next) {
          next.whenData((event) {
            setState(() {
              _recentEvents.insert(0, event);
              if (_recentEvents.length > 50) {
                _recentEvents.removeLast();
              }
            });
          });
        },
      );
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connectionState = ref.watch(currentConnectionStateProvider);
    final connectionQuality = ref.watch(connectionQualityProvider);
    final isConnected = ref.watch(isWebSocketConnectedProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Real-Time Updates'),
        actions: const [
          AppBarConnectionStatus(),
          SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Connection Status Card
          _buildConnectionCard(connectionState, connectionQuality, isConnected),

          // Recent Events List
          Expanded(
            child: _buildEventsList(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _handleReconnect,
        icon: const Icon(Icons.refresh),
        label: const Text('Reconnect'),
      ),
    );
  }

  Widget _buildConnectionCard(
    ConnectionState state,
    ConnectionQuality quality,
    bool isConnected,
  ) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  isConnected ? Icons.cloud_done : Icons.cloud_off,
                  color: isConnected ? Colors.green : Colors.red,
                  size: 32,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Connection Status',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      RealtimeStatusWidget(
                        showWhenConnected: true,
                        padding: EdgeInsets.zero,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            _buildStatusRow('State', _getStateName(state)),
            _buildStatusRow('Quality', quality.displayName),
            _buildStatusRow('Events Received', '${_recentEvents.length}'),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEventsList() {
    if (_recentEvents.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.inbox_outlined,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No events yet',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Events will appear here when received',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade500,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: _recentEvents.length,
      itemBuilder: (context, index) {
        final event = _recentEvents[index];
        return _buildEventCard(event);
      },
    );
  }

  Widget _buildEventCard(WebSocketEvent event) {
    final dateFormat = DateFormat('HH:mm:ss');

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getEventColor(event.type).withOpacity(0.2),
          child: Icon(
            _getEventIcon(event.type),
            color: _getEventColor(event.type),
            size: 20,
          ),
        ),
        title: Text(
          _getEventTypeName(event.type),
          style: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 14,
          ),
        ),
        subtitle: Text(
          dateFormat.format(event.timestamp),
          style: const TextStyle(fontSize: 12),
        ),
        trailing: const Icon(Icons.chevron_right, size: 20),
        onTap: () => _showEventDetails(event),
      ),
    );
  }

  String _getStateName(ConnectionState state) {
    switch (state) {
      case ConnectionState.connected:
        return 'Connected';
      case ConnectionState.connecting:
        return 'Connecting...';
      case ConnectionState.reconnecting:
        return 'Reconnecting...';
      case ConnectionState.disconnected:
        return 'Disconnected';
      case ConnectionState.error:
        return 'Error';
    }
  }

  String _getEventTypeName(WebSocketEventType type) {
    switch (type) {
      case WebSocketEventType.appointmentCreated:
        return 'Appointment Created';
      case WebSocketEventType.appointmentUpdated:
        return 'Appointment Updated';
      case WebSocketEventType.appointmentCancelled:
        return 'Appointment Cancelled';
      case WebSocketEventType.waitlistAdded:
        return 'Waitlist Added';
      case WebSocketEventType.waitlistUpdated:
        return 'Waitlist Updated';
      case WebSocketEventType.waitlistOfferSent:
        return 'Slot Offer Sent';
      case WebSocketEventType.notification:
        return 'Notification';
      case WebSocketEventType.heartbeat:
        return 'Heartbeat';
      case WebSocketEventType.unknown:
        return 'Unknown Event';
    }
  }

  IconData _getEventIcon(WebSocketEventType type) {
    switch (type) {
      case WebSocketEventType.appointmentCreated:
        return Icons.add_circle;
      case WebSocketEventType.appointmentUpdated:
        return Icons.edit;
      case WebSocketEventType.appointmentCancelled:
        return Icons.cancel;
      case WebSocketEventType.waitlistAdded:
        return Icons.person_add;
      case WebSocketEventType.waitlistUpdated:
        return Icons.update;
      case WebSocketEventType.waitlistOfferSent:
        return Icons.notifications_active;
      case WebSocketEventType.notification:
        return Icons.notification_important;
      case WebSocketEventType.heartbeat:
        return Icons.favorite;
      case WebSocketEventType.unknown:
        return Icons.help_outline;
    }
  }

  Color _getEventColor(WebSocketEventType type) {
    switch (type) {
      case WebSocketEventType.appointmentCreated:
        return Colors.green;
      case WebSocketEventType.appointmentUpdated:
        return Colors.blue;
      case WebSocketEventType.appointmentCancelled:
        return Colors.red;
      case WebSocketEventType.waitlistAdded:
        return Colors.purple;
      case WebSocketEventType.waitlistUpdated:
        return Colors.indigo;
      case WebSocketEventType.waitlistOfferSent:
        return Colors.orange;
      case WebSocketEventType.notification:
        return Colors.amber;
      case WebSocketEventType.heartbeat:
        return Colors.pink;
      case WebSocketEventType.unknown:
        return Colors.grey;
    }
  }

  void _showEventDetails(WebSocketEvent event) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_getEventTypeName(event.type)),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Timestamp',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.grey.shade700,
                ),
              ),
              const SizedBox(height: 4),
              Text(DateFormat('yyyy-MM-dd HH:mm:ss').format(event.timestamp)),
              const SizedBox(height: 16),
              Text(
                'Data',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.grey.shade700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                event.data.toString(),
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Future<void> _handleReconnect() async {
    final manager = ref.read(realtimeConnectionManagerProvider);

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            ),
            SizedBox(width: 12),
            Text('Reconnecting...'),
          ],
        ),
        duration: Duration(seconds: 2),
      ),
    );

    await manager.reconnect();
  }
}
