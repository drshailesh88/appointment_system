import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/noshow_prediction.dart';
import '../../../core/providers/noshow_provider.dart';

/// Visual risk indicator widget for no-show predictions
///
/// Displays:
/// - Color-coded badge based on risk level
/// - Probability percentage
/// - Tooltip with detailed information
/// - Action buttons for mitigation
class NoShowRiskIndicator extends ConsumerWidget {
  final String appointmentId;
  final bool showDetails;
  final bool showActions;
  final VoidCallback? onTap;

  const NoShowRiskIndicator({
    super.key,
    required this.appointmentId,
    this.showDetails = false,
    this.showActions = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Auto-load prediction if not cached
    final predictionAsync = ref.watch(autoPredict(appointmentId));

    return predictionAsync.when(
      data: (prediction) {
        if (prediction == null) {
          return const SizedBox.shrink();
        }

        return _buildIndicator(context, prediction);
      },
      loading: () => const SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      error: (error, stack) => const SizedBox.shrink(),
    );
  }

  Widget _buildIndicator(BuildContext context, NoShowPrediction prediction) {
    final colors = _getRiskColors(prediction.riskLevel);

    if (showDetails) {
      return _buildDetailedCard(context, prediction, colors);
    } else {
      return _buildCompactBadge(context, prediction, colors);
    }
  }

  Widget _buildCompactBadge(
    BuildContext context,
    NoShowPrediction prediction,
    RiskColors colors,
  ) {
    final badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.border, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getRiskIcon(prediction.riskLevel),
            size: 14,
            color: colors.foreground,
          ),
          const SizedBox(width: 4),
          Text(
            '${prediction.riskPercentage}%',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: colors.foreground,
            ),
          ),
        ],
      ),
    );

    // Wrap in tooltip
    return Tooltip(
      message: _buildTooltipMessage(prediction),
      child: onTap != null
          ? InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(12),
              child: badge,
            )
          : badge,
    );
  }

  Widget _buildDetailedCard(
    BuildContext context,
    NoShowPrediction prediction,
    RiskColors colors,
  ) {
    return Card(
      color: colors.background.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with risk level
            Row(
              children: [
                Icon(
                  _getRiskIcon(prediction.riskLevel),
                  color: colors.foreground,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  '${_getRiskLabel(prediction.riskLevel)} Risk',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: colors.foreground,
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: colors.background,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Text(
                    '${prediction.riskPercentage}%',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: colors.foreground,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Risk explanation
            Text(
              _getRiskExplanation(prediction),
              style: Theme.of(context).textTheme.bodySmall,
            ),

            // Actions (if enabled)
            if (showActions && prediction.recommendedActions.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 8),
              Text(
                'Recommended Actions:',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              ...prediction.recommendedActions
                  .map((action) => _buildActionItem(context, action)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionItem(BuildContext context, MitigationAction action) {
    final icon = _getActionIcon(action.action);
    final priorityColor = _getPriorityColor(action.priority);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: priorityColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Icon(icon, size: 16, color: priorityColor),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  action.description,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (action.isHighPriority)
                  Text(
                    'High Priority',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: priorityColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 10,
                        ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _buildTooltipMessage(NoShowPrediction prediction) {
    final riskLabel = _getRiskLabel(prediction.riskLevel);
    final buffer = StringBuffer();

    buffer.writeln('$riskLabel Risk: ${prediction.riskPercentage}%');
    buffer.writeln('');

    if (prediction.recommendedActions.isNotEmpty) {
      buffer.writeln('Actions:');
      for (final action in prediction.recommendedActions) {
        buffer.writeln('• ${action.description}');
      }
    }

    return buffer.toString().trim();
  }

  String _getRiskExplanation(NoShowPrediction prediction) {
    final features = prediction.featuresUsed;

    if (prediction.isHighRisk) {
      if (features['is_new_patient'] == 1) {
        return 'New patient with high no-show likelihood based on booking patterns.';
      } else if ((features['no_show_rate'] as num?) ?? 0 > 0.3) {
        return 'Patient has a history of missing appointments.';
      } else if ((features['lead_time_days'] as num?) ?? 0 > 14) {
        return 'Appointment scheduled too far in advance.';
      } else {
        return 'Multiple risk factors detected for this appointment.';
      }
    } else if (prediction.isMediumRisk) {
      return 'Some risk factors present. Consider sending extra reminders.';
    } else {
      return 'Low risk of no-show. Standard reminder should suffice.';
    }
  }

  String _getRiskLabel(String riskLevel) {
    switch (riskLevel) {
      case 'high':
        return 'High';
      case 'medium':
        return 'Medium';
      case 'low':
        return 'Low';
      default:
        return 'Unknown';
    }
  }

  IconData _getRiskIcon(String riskLevel) {
    switch (riskLevel) {
      case 'high':
        return Icons.warning_amber_rounded;
      case 'medium':
        return Icons.info_outline;
      case 'low':
        return Icons.check_circle_outline;
      default:
        return Icons.help_outline;
    }
  }

  RiskColors _getRiskColors(String riskLevel) {
    switch (riskLevel) {
      case 'high':
        return RiskColors(
          foreground: const Color(0xFFD32F2F),
          background: const Color(0xFFFFEBEE),
          border: const Color(0xFFEF5350),
        );
      case 'medium':
        return RiskColors(
          foreground: const Color(0xFFF57C00),
          background: const Color(0xFFFFF3E0),
          border: const Color(0xFFFFB74D),
        );
      case 'low':
        return RiskColors(
          foreground: const Color(0xFF388E3C),
          background: const Color(0xFFE8F5E9),
          border: const Color(0xFF66BB6A),
        );
      default:
        return RiskColors(
          foreground: const Color(0xFF757575),
          background: const Color(0xFFF5F5F5),
          border: const Color(0xFFBDBDBD),
        );
    }
  }

  IconData _getActionIcon(String actionType) {
    if (actionType.contains('call')) {
      return Icons.phone;
    } else if (actionType.contains('reminder')) {
      return Icons.notifications;
    } else if (actionType.contains('welcome')) {
      return Icons.waving_hand;
    } else if (actionType.contains('reschedule')) {
      return Icons.schedule;
    } else {
      return Icons.task_alt;
    }
  }

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'high':
        return const Color(0xFFD32F2F);
      case 'medium':
        return const Color(0xFFF57C00);
      case 'low':
        return const Color(0xFF388E3C);
      default:
        return const Color(0xFF757575);
    }
  }
}

/// Color scheme for risk levels
class RiskColors {
  final Color foreground;
  final Color background;
  final Color border;

  RiskColors({
    required this.foreground,
    required this.background,
    required this.border,
  });
}

/// Compact no-show risk badge for list items
class NoShowRiskBadge extends ConsumerWidget {
  final String appointmentId;

  const NoShowRiskBadge({
    super.key,
    required this.appointmentId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return NoShowRiskIndicator(
      appointmentId: appointmentId,
      showDetails: false,
      showActions: false,
    );
  }
}

/// Detailed no-show risk card
class NoShowRiskCard extends ConsumerWidget {
  final String appointmentId;
  final bool showActions;

  const NoShowRiskCard({
    super.key,
    required this.appointmentId,
    this.showActions = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return NoShowRiskIndicator(
      appointmentId: appointmentId,
      showDetails: true,
      showActions: showActions,
    );
  }
}

/// High-risk appointments summary widget
class HighRiskSummary extends ConsumerWidget {
  const HighRiskSummary({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final highRiskCount = ref.watch(highRiskCountProvider);

    if (highRiskCount == 0) {
      return const SizedBox.shrink();
    }

    return Card(
      color: const Color(0xFFFFEBEE),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(
              Icons.warning_amber_rounded,
              color: Color(0xFFD32F2F),
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$highRiskCount High-Risk Appointment${highRiskCount > 1 ? 's' : ''}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Color(0xFFD32F2F),
                    ),
                  ),
                  const Text(
                    'Review and send confirmation calls',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF757575),
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.arrow_forward),
              onPressed: () {
                // Navigate to high-risk appointments list
              },
            ),
          ],
        ),
      ),
    );
  }
}
