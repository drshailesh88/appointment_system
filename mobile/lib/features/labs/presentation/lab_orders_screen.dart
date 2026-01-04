import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/models/lab_result.dart';
import '../../../core/providers/labs_provider.dart';
import 'lab_result_screen.dart';

/// Lab orders screen showing all lab orders for a patient
class LabOrdersScreen extends ConsumerStatefulWidget {
  final String patientId;
  final String? patientName;

  const LabOrdersScreen({
    super.key,
    required this.patientId,
    this.patientName,
  });

  @override
  ConsumerState<LabOrdersScreen> createState() => _LabOrdersScreenState();
}

class _LabOrdersScreenState extends ConsumerState<LabOrdersScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);

    // Load orders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(labOrdersProvider.notifier).loadPatientOrders(widget.patientId);
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(labOrdersProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Lab Results'),
            if (widget.patientName != null)
              Text(
                widget.patientName!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.white70,
                    ),
              ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'New Lab Order',
            onPressed: () => _showNewOrderDialog(),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () =>
                ref.read(labOrdersProvider.notifier).loadPatientOrders(
                      widget.patientId,
                    ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: 'All (${state.orders.length})'),
            Tab(text: 'Pending (${state.pendingOrders.length})'),
            Tab(text: 'Completed (${state.completedOrders.length})'),
          ],
        ),
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _buildError(state.error!)
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildOrdersList(state.orders),
                    _buildOrdersList(state.pendingOrders),
                    _buildOrdersList(state.completedOrders),
                  ],
                ),
    );
  }

  Widget _buildError(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          Text(
            'Error loading lab orders',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(error),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () =>
                ref.read(labOrdersProvider.notifier).loadPatientOrders(
                      widget.patientId,
                    ),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildOrdersList(List<LabOrder> orders) {
    if (orders.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.science_outlined,
              size: 64,
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              'No lab orders',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 8),
            const Text('Tap + to create a new lab order'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(labOrdersProvider.notifier).loadPatientOrders(
              widget.patientId,
            );
      },
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: orders.length,
        separatorBuilder: (context, index) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          return _LabOrderCard(
            order: orders[index],
            onTap: () => _navigateToResults(orders[index]),
          );
        },
      ),
    );
  }

  void _navigateToResults(LabOrder order) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => LabResultScreen(
          orderId: order.id,
          orderDate: order.orderDate,
          patientName: widget.patientName,
        ),
      ),
    );
  }

  void _showNewOrderDialog() {
    // TODO: Implement new order creation dialog
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('New order creation coming soon'),
      ),
    );
  }
}

/// Lab order card widget
class _LabOrderCard extends StatelessWidget {
  final LabOrder order;
  final VoidCallback onTap;

  const _LabOrderCard({
    required this.order,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  // Status chip
                  _StatusChip(
                    status: order.status,
                    statusDisplay: order.statusDisplay,
                  ),
                  const Spacer(),
                  // Priority badge
                  if (order.priority != 'routine')
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: _getPriorityColor(order.priority),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        order.priorityDisplay,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Order date
              Row(
                children: [
                  Icon(
                    Icons.calendar_today,
                    size: 16,
                    color: Colors.grey[600],
                  ),
                  const SizedBox(width: 8),
                  Text(
                    DateFormat('MMM dd, yyyy').format(order.orderDate),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: Colors.grey[700],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Tests ordered
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.science,
                    size: 16,
                    color: Colors.grey[600],
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      order.testsOrdered.join(', '),
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),

              // Doctor
              if (order.doctorName != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.person,
                      size: 16,
                      color: Colors.grey[600],
                    ),
                    const SizedBox(width: 8),
                    Text(
                      order.doctorName!,
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
              ],

              // Lab provider
              if (order.labProvider != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.local_hospital,
                      size: 16,
                      color: Colors.grey[600],
                    ),
                    const SizedBox(width: 8),
                    Text(
                      order.labProvider!,
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
              ],

              // Results summary
              if (order.resultsCount > 0) ...[
                const Divider(height: 24),
                Row(
                  children: [
                    _ResultBadge(
                      icon: Icons.check_circle_outline,
                      label: '${order.resultsCount} Results',
                      color: Colors.blue,
                    ),
                    const SizedBox(width: 16),
                    if (order.abnormalCount > 0)
                      _ResultBadge(
                        icon: Icons.warning_amber_outlined,
                        label: '${order.abnormalCount} Abnormal',
                        color: Colors.orange,
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'urgent':
        return Colors.orange;
      case 'stat':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }
}

/// Status chip widget
class _StatusChip extends StatelessWidget {
  final String status;
  final String statusDisplay;

  const _StatusChip({
    required this.status,
    required this.statusDisplay,
  });

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData icon;

    switch (status) {
      case 'ordered':
        color = Colors.blue;
        icon = Icons.pending_outlined;
        break;
      case 'sample_collected':
        color = Colors.lightBlue;
        icon = Icons.science_outlined;
        break;
      case 'in_progress':
        color = Colors.orange;
        icon = Icons.hourglass_empty;
        break;
      case 'completed':
        color = Colors.green;
        icon = Icons.check_circle_outline;
        break;
      case 'cancelled':
        color = Colors.red;
        icon = Icons.cancel_outlined;
        break;
      default:
        color = Colors.grey;
        icon = Icons.help_outline;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            statusDisplay,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Result badge widget
class _ResultBadge extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;

  const _ResultBadge({
    required this.icon,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
