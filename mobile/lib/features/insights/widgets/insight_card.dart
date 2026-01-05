import 'package:flutter/material.dart';

import '../../../core/models/insight.dart';
import 'insight_action_button.dart';
import 'priority_badge.dart';

/// Insight Card Widget
///
/// Displays a single insight with actions.
class InsightCard extends StatelessWidget {
  final Insight insight;
  final VoidCallback? onTap;
  final Future<bool> Function(String actionType, Map<String, dynamic>? params)?
      onAction;
  final VoidCallback? onDismiss;
  final void Function(int minutes)? onSnooze;

  const InsightCard({
    Key? key,
    required this.insight,
    this.onTap,
    this.onAction,
    this.onDismiss,
    this.onSnooze,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: _getPriorityColor(insight.priority).withOpacity(0.3),
          width: 1,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header: Category, Priority, Dismiss
              Row(
                children: [
                  // Category icon
                  Icon(
                    _getCategoryIcon(insight.category),
                    size: 20,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    insight.categoryDisplay,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                  const Spacer(),
                  PriorityBadge(priority: insight.priority),
                  const SizedBox(width: 8),
                  // Dismiss button
                  if (onDismiss != null)
                    IconButton(
                      icon: const Icon(Icons.close, size: 18),
                      onPressed: onDismiss,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Title
              Text(
                insight.title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),

              // Description
              Text(
                insight.description,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey[700],
                    ),
              ),

              // Actions
              if (insight.suggestedActions != null &&
                  insight.suggestedActions!.isNotEmpty) ...[
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: insight.suggestedActions!
                      .map((action) => InsightActionButton(
                            label: action.label,
                            onPressed: onAction != null
                                ? () => onAction!(
                                      action.actionType,
                                      action.params,
                                    )
                                : null,
                          ))
                      .toList(),
                ),
              ],

              // Snooze options
              if (onSnooze != null) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    TextButton.icon(
                      onPressed: () => onSnooze!(30),
                      icon: const Icon(Icons.snooze, size: 16),
                      label: const Text('30m'),
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                    ),
                    TextButton.icon(
                      onPressed: () => onSnooze!(60),
                      icon: const Icon(Icons.snooze, size: 16),
                      label: const Text('1h'),
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                    ),
                    TextButton.icon(
                      onPressed: () => onSnooze!(240),
                      icon: const Icon(Icons.snooze, size: 16),
                      label: const Text('4h'),
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                    ),
                  ],
                ),
              ],

              // Timestamp
              const SizedBox(height: 8),
              Text(
                _formatTimestamp(insight.createdAt),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[500],
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getPriorityColor(InsightPriority priority) {
    switch (priority) {
      case InsightPriority.urgent:
        return Colors.red;
      case InsightPriority.important:
        return Colors.orange;
      case InsightPriority.info:
        return Colors.blue;
    }
  }

  IconData _getCategoryIcon(InsightCategory category) {
    switch (category) {
      case InsightCategory.followUp:
        return Icons.event_repeat;
      case InsightCategory.schedule:
        return Icons.schedule;
      case InsightCategory.revenue:
        return Icons.account_balance_wallet;
      case InsightCategory.anomaly:
        return Icons.warning_amber_rounded;
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
}
