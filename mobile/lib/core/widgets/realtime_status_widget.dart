import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/realtime_provider.dart';
import '../services/websocket_service.dart';

/// Widget to display real-time connection status
class RealtimeStatusWidget extends ConsumerWidget {
  final bool showWhenConnected;
  final EdgeInsetsGeometry? padding;

  const RealtimeStatusWidget({
    super.key,
    this.showWhenConnected = false,
    this.padding,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final connectionState = ref.watch(currentConnectionStateProvider);
    final connectionQuality = ref.watch(connectionQualityProvider);

    // Don't show anything if connected (and showWhenConnected is false)
    if (connectionQuality.isConnected && !showWhenConnected) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: padding ?? const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildStatusIndicator(connectionState),
          const SizedBox(width: 8),
          Text(
            connectionQuality.displayName,
            style: TextStyle(
              fontSize: 12,
              color: _getStatusColor(connectionState),
              fontWeight: FontWeight.w500,
            ),
          ),
          if (connectionState == ConnectionState.reconnecting ||
              connectionState == ConnectionState.connecting)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: SizedBox(
                width: 12,
                height: 12,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _getStatusColor(connectionState),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildStatusIndicator(ConnectionState state) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _getStatusColor(state),
        boxShadow: state == ConnectionState.connected
            ? [
                BoxShadow(
                  color: _getStatusColor(state).withOpacity(0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
    );
  }

  Color _getStatusColor(ConnectionState state) {
    switch (state) {
      case ConnectionState.connected:
        return Colors.green;
      case ConnectionState.connecting:
      case ConnectionState.reconnecting:
        return Colors.orange;
      case ConnectionState.disconnected:
      case ConnectionState.error:
        return Colors.red;
    }
  }
}

/// Compact connection status badge
class RealtimeStatusBadge extends ConsumerWidget {
  const RealtimeStatusBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isConnected = ref.watch(isWebSocketConnectedProvider);

    if (isConnected) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.shade200),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.cloud_off, size: 14, color: Colors.red.shade700),
          const SizedBox(width: 4),
          Text(
            'Offline',
            style: TextStyle(
              fontSize: 11,
              color: Colors.red.shade700,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Connection status indicator for app bar
class AppBarConnectionStatus extends ConsumerWidget {
  const AppBarConnectionStatus({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final connectionQuality = ref.watch(connectionQualityProvider);

    if (connectionQuality.isConnected) {
      return const SizedBox.shrink();
    }

    return IconButton(
      icon: Stack(
        children: [
          const Icon(Icons.sync),
          if (connectionQuality == ConnectionQuality.connecting ||
              connectionQuality == ConnectionQuality.degraded)
            Positioned(
              right: 0,
              bottom: 0,
              child: Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: connectionQuality == ConnectionQuality.connecting
                      ? Colors.orange
                      : Colors.red,
                ),
              ),
            ),
        ],
      ),
      onPressed: () async {
        final manager = ref.read(realtimeConnectionManagerProvider);
        await manager.reconnect();
      },
      tooltip: 'Reconnect to server',
    );
  }
}

/// Snackbar helper for connection status changes
class RealtimeConnectionSnackbar extends ConsumerStatefulWidget {
  final Widget child;

  const RealtimeConnectionSnackbar({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<RealtimeConnectionSnackbar> createState() =>
      _RealtimeConnectionSnackbarState();
}

class _RealtimeConnectionSnackbarState
    extends ConsumerState<RealtimeConnectionSnackbar> {
  ConnectionState? _previousState;

  @override
  Widget build(BuildContext context) {
    ref.listen<ConnectionState>(
      currentConnectionStateProvider,
      (previous, next) {
        // Only show snackbar on state changes
        if (previous != null && previous != next) {
          _showConnectionSnackbar(context, next, previous);
        }
        _previousState = next;
      },
    );

    return widget.child;
  }

  void _showConnectionSnackbar(
    BuildContext context,
    ConnectionState current,
    ConnectionState previous,
  ) {
    // Don't show snackbar for minor state transitions
    if (current == ConnectionState.connecting ||
        current == ConnectionState.reconnecting) {
      return;
    }

    String message;
    Color backgroundColor;
    IconData icon;

    switch (current) {
      case ConnectionState.connected:
        // Only show "reconnected" message if we were previously disconnected
        if (previous == ConnectionState.disconnected ||
            previous == ConnectionState.error) {
          message = 'Connected to server';
          backgroundColor = Colors.green;
          icon = Icons.cloud_done;
        } else {
          return; // Don't show snackbar
        }
        break;

      case ConnectionState.disconnected:
        message = 'Disconnected from server';
        backgroundColor = Colors.orange;
        icon = Icons.cloud_off;
        break;

      case ConnectionState.error:
        message = 'Connection error';
        backgroundColor = Colors.red;
        icon = Icons.error_outline;
        break;

      default:
        return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(icon, color: Colors.white),
            const SizedBox(width: 12),
            Text(message),
          ],
        ),
        backgroundColor: backgroundColor,
        duration: const Duration(seconds: 3),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
