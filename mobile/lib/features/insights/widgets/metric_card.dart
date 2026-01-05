import 'package:flutter/material.dart';

import '../../../core/models/daily_digest.dart';

/// Metric Card Widget
///
/// Displays a key metric with trend indicator.
class MetricCard extends StatelessWidget {
  final DigestMetric metric;
  final VoidCallback? onTap;

  const MetricCard({
    Key? key,
    required this.metric,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Icon and label
              Row(
                children: [
                  if (metric.icon != null) ...[
                    Icon(
                      _getIcon(metric.icon!),
                      size: 20,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                  ],
                  Expanded(
                    child: Text(
                      metric.label,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                            fontWeight: FontWeight.w500,
                          ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Value
              Text(
                metric.value,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),

              // Trend indicator
              if (metric.trend != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      _getTrendIcon(metric),
                      size: 16,
                      color: _getTrendColor(metric),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      metric.trendPercentage ?? metric.trend!,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: _getTrendColor(metric),
                      ),
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

  IconData _getIcon(String iconName) {
    switch (iconName) {
      case 'appointments':
        return Icons.event;
      case 'patients':
        return Icons.people;
      case 'revenue':
        return Icons.attach_money;
      case 'procedures':
        return Icons.medical_services;
      case 'no_shows':
        return Icons.event_busy;
      case 'cancellations':
        return Icons.cancel;
      default:
        return Icons.analytics;
    }
  }

  IconData _getTrendIcon(DigestMetric metric) {
    if (metric.isUpTrend) {
      return Icons.trending_up;
    } else if (metric.isDownTrend) {
      return Icons.trending_down;
    } else {
      return Icons.trending_flat;
    }
  }

  Color _getTrendColor(DigestMetric metric) {
    if (metric.isUpTrend) {
      return Colors.green;
    } else if (metric.isDownTrend) {
      return Colors.red;
    } else {
      return Colors.grey;
    }
  }
}
