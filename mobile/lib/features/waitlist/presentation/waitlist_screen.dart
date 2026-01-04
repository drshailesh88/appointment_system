import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/waitlist_provider.dart';

/// Waitlist management screen
class WaitlistScreen extends ConsumerStatefulWidget {
  const WaitlistScreen({super.key});

  @override
  ConsumerState<WaitlistScreen> createState() => _WaitlistScreenState();
}

class _WaitlistScreenState extends ConsumerState<WaitlistScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String? _selectedDoctorId;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(waitlistProvider.notifier).loadWaitlist();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(waitlistProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Waitlist'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Waiting'),
            Tab(text: 'Offered'),
            Tab(text: 'All'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () => _showFilterDialog(),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(waitlistProvider.notifier).loadWaitlist(),
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _buildErrorView(state.error!)
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildWaitlistTab(state.waitingEntries),
                    _buildOfferedTab(state.offeredEntries),
                    _buildAllTab(state.entries),
                  ],
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddToWaitlistDialog(),
        icon: const Icon(Icons.add),
        label: const Text('Add to Waitlist'),
      ),
    );
  }

  Widget _buildErrorView(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.red.shade300),
          const SizedBox(height: 16),
          Text('Error: $error'),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => ref.read(waitlistProvider.notifier).loadWaitlist(),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildWaitlistTab(List<WaitlistEntry> entries) {
    if (entries.isEmpty) {
      return _buildEmptyState(
        'No patients waiting',
        'Patients will appear here when slots are full',
      );
    }

    // Group by priority
    final emergencyEntries = entries
        .where((e) => e.priority == WaitlistPriority.emergency)
        .toList();
    final urgentEntries =
        entries.where((e) => e.priority == WaitlistPriority.urgent).toList();
    final normalEntries =
        entries.where((e) => e.priority == WaitlistPriority.normal).toList();
    final flexibleEntries =
        entries.where((e) => e.priority == WaitlistPriority.flexible).toList();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (emergencyEntries.isNotEmpty) ...[
          _buildPriorityHeader('Emergency', Colors.red, emergencyEntries.length),
          ...emergencyEntries.map((e) => _buildWaitlistCard(e)),
          const SizedBox(height: 16),
        ],
        if (urgentEntries.isNotEmpty) ...[
          _buildPriorityHeader('Urgent', Colors.orange, urgentEntries.length),
          ...urgentEntries.map((e) => _buildWaitlistCard(e)),
          const SizedBox(height: 16),
        ],
        if (normalEntries.isNotEmpty) ...[
          _buildPriorityHeader('Normal', Colors.blue, normalEntries.length),
          ...normalEntries.map((e) => _buildWaitlistCard(e)),
          const SizedBox(height: 16),
        ],
        if (flexibleEntries.isNotEmpty) ...[
          _buildPriorityHeader('Flexible', Colors.green, flexibleEntries.length),
          ...flexibleEntries.map((e) => _buildWaitlistCard(e)),
        ],
      ],
    );
  }

  Widget _buildOfferedTab(List<WaitlistEntry> entries) {
    if (entries.isEmpty) {
      return _buildEmptyState(
        'No pending offers',
        'Slot offers will appear here when cancellations occur',
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: entries.length,
      itemBuilder: (context, index) {
        return _buildOfferedCard(entries[index]);
      },
    );
  }

  Widget _buildAllTab(List<WaitlistEntry> entries) {
    if (entries.isEmpty) {
      return _buildEmptyState(
        'Waitlist is empty',
        'Add patients when all appointment slots are booked',
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: entries.length,
      itemBuilder: (context, index) {
        return _buildWaitlistCard(entries[index]);
      },
    );
  }

  Widget _buildEmptyState(String title, String subtitle) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.hourglass_empty, size: 64, color: Colors.grey.shade400),
          const SizedBox(height: 16),
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey,
                ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildPriorityHeader(String title, Color color, int count) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(width: 8),
          Chip(
            label: Text('$count'),
            labelStyle: const TextStyle(fontSize: 12),
            padding: EdgeInsets.zero,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ],
      ),
    );
  }

  Widget _buildWaitlistCard(WaitlistEntry entry) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getPriorityColor(entry.priority).withOpacity(0.2),
          child: Text(
            entry.patientName.substring(0, 1).toUpperCase(),
            style: TextStyle(
              color: _getPriorityColor(entry.priority),
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        title: Text(entry.patientName),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (entry.doctorName != null)
              Text('Doctor: ${entry.doctorName}'),
            if (entry.preferredDate != null)
              Text('Preferred: ${entry.preferredDate} ${entry.preferredTimeSlot ?? ""}'),
            Text(
              'Queue Position: #${entry.queuePosition}',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildStatusChip(entry.status),
            PopupMenuButton<String>(
              onSelected: (value) => _handleMenuAction(value, entry),
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'priority',
                  child: ListTile(
                    leading: Icon(Icons.flag),
                    title: Text('Change Priority'),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
                const PopupMenuItem(
                  value: 'cancel',
                  child: ListTile(
                    leading: Icon(Icons.cancel, color: Colors.red),
                    title: Text('Cancel', style: TextStyle(color: Colors.red)),
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ],
            ),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }

  Widget _buildOfferedCard(WaitlistEntry entry) {
    final remainingTime = entry.expiresAt?.difference(DateTime.now());
    final isExpiringSoon = remainingTime != null && remainingTime.inMinutes < 10;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: isExpiringSoon ? Colors.orange.shade50 : null,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: Colors.green.shade100,
                  child: const Icon(Icons.check_circle, color: Colors.green),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.patientName,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      Text('Slot offered - waiting for response'),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (entry.expiresAt != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: isExpiringSoon ? Colors.orange.shade100 : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.timer,
                      size: 16,
                      color: isExpiringSoon ? Colors.orange : Colors.grey,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Expires in ${remainingTime?.inMinutes ?? 0} minutes',
                      style: TextStyle(
                        color: isExpiringSoon ? Colors.orange.shade800 : Colors.grey.shade700,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => _declineSlot(entry),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.red,
                  ),
                  child: const Text('Decline'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () => _confirmSlot(entry),
                  child: const Text('Confirm Booking'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusChip(WaitlistStatus status) {
    Color color;
    switch (status) {
      case WaitlistStatus.waiting:
        color = Colors.blue;
        break;
      case WaitlistStatus.offered:
        color = Colors.green;
        break;
      case WaitlistStatus.confirmed:
        color = Colors.teal;
        break;
      case WaitlistStatus.expired:
        color = Colors.orange;
        break;
      case WaitlistStatus.cancelled:
        color = Colors.red;
        break;
    }

    return Chip(
      label: Text(
        status.displayName,
        style: TextStyle(fontSize: 12, color: color),
      ),
      backgroundColor: color.withOpacity(0.1),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Color _getPriorityColor(WaitlistPriority priority) {
    switch (priority) {
      case WaitlistPriority.emergency:
        return Colors.red;
      case WaitlistPriority.urgent:
        return Colors.orange;
      case WaitlistPriority.normal:
        return Colors.blue;
      case WaitlistPriority.flexible:
        return Colors.green;
    }
  }

  void _handleMenuAction(String action, WaitlistEntry entry) {
    switch (action) {
      case 'priority':
        _showPriorityDialog(entry);
        break;
      case 'cancel':
        _cancelEntry(entry);
        break;
    }
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Waitlist'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('All Doctors'),
              leading: Radio<String?>(
                value: null,
                groupValue: _selectedDoctorId,
                onChanged: (value) {
                  setState(() => _selectedDoctorId = value);
                  Navigator.pop(context);
                  ref.read(waitlistProvider.notifier).loadWaitlist(
                        doctorId: value,
                      );
                },
              ),
            ),
          ],
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

  void _showAddToWaitlistDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add to Waitlist'),
        content: const Text(
          'Use the patient search to find and add a patient to the waitlist when all slots are booked.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // Navigate to patient search
            },
            child: const Text('Search Patient'),
          ),
        ],
      ),
    );
  }

  void _showPriorityDialog(WaitlistEntry entry) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Change Priority'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: WaitlistPriority.values.map((priority) {
            return ListTile(
              leading: CircleAvatar(
                backgroundColor: _getPriorityColor(priority),
                radius: 12,
              ),
              title: Text(priority.displayName),
              selected: entry.priority == priority,
              onTap: () {
                Navigator.pop(context);
                _updatePriority(entry, priority);
              },
            );
          }).toList(),
        ),
      ),
    );
  }

  Future<void> _confirmSlot(WaitlistEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm Booking'),
        content: Text(
          'Confirm appointment for ${entry.patientName}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final success =
          await ref.read(waitlistProvider.notifier).confirmSlot(entry.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              success ? 'Appointment confirmed' : 'Failed to confirm appointment',
            ),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _declineSlot(WaitlistEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Decline Slot'),
        content: const Text(
          'The patient will remain on the waitlist for the next available slot.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
            ),
            child: const Text('Decline'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final success =
          await ref.read(waitlistProvider.notifier).declineSlot(entry.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              success ? 'Slot declined' : 'Failed to decline slot',
            ),
          ),
        );
      }
    }
  }

  Future<void> _cancelEntry(WaitlistEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Waitlist Entry'),
        content: Text(
          'Remove ${entry.patientName} from the waitlist?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Keep'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final success =
          await ref.read(waitlistProvider.notifier).cancelEntry(entry.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              success ? 'Removed from waitlist' : 'Failed to remove',
            ),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _updatePriority(
      WaitlistEntry entry, WaitlistPriority priority) async {
    final success = await ref
        .read(waitlistProvider.notifier)
        .updatePriority(entry.id, priority.name);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            success
                ? 'Priority updated to ${priority.displayName}'
                : 'Failed to update priority',
          ),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
    }
  }
}
