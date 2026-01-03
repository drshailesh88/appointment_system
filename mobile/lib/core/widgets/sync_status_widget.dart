import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/sync_provider.dart';

/// Widget to display sync status in app bar
class SyncStatusWidget extends ConsumerWidget {
  const SyncStatusWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final syncState = ref.watch(syncProvider);

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Offline indicator
        if (!syncState.isOnline)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.orange.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.cloud_off,
                  size: 16,
                  color: Colors.orange.shade700,
                ),
                const SizedBox(width: 4),
                Text(
                  'Offline',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.orange.shade700,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),

        // Pending sync indicator
        if (syncState.hasPendingChanges && syncState.isOnline)
          InkWell(
            onTap: () => ref.read(syncProvider.notifier).syncNow(),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.blue.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (syncState.isSyncing)
                    SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.blue.shade700,
                      ),
                    )
                  else
                    Icon(
                      Icons.sync,
                      size: 16,
                      color: Colors.blue.shade700,
                    ),
                  const SizedBox(width: 4),
                  Text(
                    '${syncState.pendingCount} pending',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.blue.shade700,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// Full sync status banner for showing at top of screen
class SyncStatusBanner extends ConsumerWidget {
  const SyncStatusBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final syncState = ref.watch(syncProvider);

    if (syncState.isOnline && !syncState.hasPendingChanges) {
      return const SizedBox.shrink();
    }

    return Material(
      color: syncState.isOnline ? Colors.blue.shade50 : Colors.orange.shade50,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Icon(
                syncState.isOnline ? Icons.sync : Icons.cloud_off,
                color: syncState.isOnline
                    ? Colors.blue.shade700
                    : Colors.orange.shade700,
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      syncState.isOnline
                          ? 'Syncing changes...'
                          : 'You are offline',
                      style: TextStyle(
                        fontWeight: FontWeight.w500,
                        color: syncState.isOnline
                            ? Colors.blue.shade700
                            : Colors.orange.shade700,
                      ),
                    ),
                    if (syncState.hasPendingChanges)
                      Text(
                        '${syncState.pendingCount} changes pending',
                        style: TextStyle(
                          fontSize: 12,
                          color: syncState.isOnline
                              ? Colors.blue.shade600
                              : Colors.orange.shade600,
                        ),
                      ),
                  ],
                ),
              ),
              if (syncState.isOnline && !syncState.isSyncing)
                TextButton(
                  onPressed: () => ref.read(syncProvider.notifier).syncNow(),
                  child: const Text('Sync Now'),
                ),
              if (syncState.isSyncing)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Floating sync button for bottom of screen
class SyncFloatingButton extends ConsumerWidget {
  const SyncFloatingButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final syncState = ref.watch(syncProvider);

    if (!syncState.hasPendingChanges) {
      return const SizedBox.shrink();
    }

    return FloatingActionButton.small(
      onPressed: syncState.isSyncing
          ? null
          : () => ref.read(syncProvider.notifier).syncNow(),
      backgroundColor: syncState.isOnline ? Colors.blue : Colors.grey,
      child: syncState.isSyncing
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : Badge(
              label: Text('${syncState.pendingCount}'),
              child: const Icon(Icons.sync),
            ),
    );
  }
}
