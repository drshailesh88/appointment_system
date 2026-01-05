import 'package:flutter/material.dart';

import '../../../core/models/insight.dart';

/// Priority Badge Widget
///
/// Displays priority indicator with color coding.
class PriorityBadge extends StatelessWidget {
  final InsightPriority priority;
  final bool showLabel;
  final double size;

  const PriorityBadge({
    Key? key,
    required this.priority,
    this.showLabel = true,
    this.size = 20,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final color = _getPriorityColor(priority);
    final icon = _getPriorityIcon(priority);

    if (showLabel) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 4),
            Text(
              _getPriorityLabel(priority),
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
      child: Icon(
        icon,
        size: size * 0.6,
        color: Colors.white,
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

  IconData _getPriorityIcon(InsightPriority priority) {
    switch (priority) {
      case InsightPriority.urgent:
        return Icons.priority_high;
      case InsightPriority.important:
        return Icons.flag;
      case InsightPriority.info:
        return Icons.info_outline;
    }
  }

  String _getPriorityLabel(InsightPriority priority) {
    switch (priority) {
      case InsightPriority.urgent:
        return 'Urgent';
      case InsightPriority.important:
        return 'Important';
      case InsightPriority.info:
        return 'Info';
    }
  }
}
