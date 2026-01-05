import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/providers/nl_search_provider.dart';

/// Search Result Card Widget
///
/// Displays a single appointment search result with relevance information
class SearchResultCard extends StatelessWidget {
  final AppointmentSearchResult result;

  const SearchResultCard({
    super.key,
    required this.result,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: _getStatusColor(result.status).withOpacity(0.3),
          width: 2,
        ),
      ),
      child: InkWell(
        onTap: () => _onTap(context),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header: Patient Name + Status
              Row(
                children: [
                  Expanded(
                    child: Text(
                      result.patientName,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _StatusBadge(
                    status: result.status,
                    label: result.statusLabel,
                    icon: result.statusIcon,
                  ),
                ],
              ),

              const SizedBox(height: 8),

              // Date & Time
              Row(
                children: [
                  Icon(
                    Icons.calendar_today,
                    size: 16,
                    color: theme.textTheme.bodySmall?.color,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _formatDateTime(result.scheduledStart),
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(width: 16),
                  Icon(
                    Icons.access_time,
                    size: 16,
                    color: theme.textTheme.bodySmall?.color,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _formatTime(result.scheduledStart),
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ),

              const SizedBox(height: 8),

              // Doctor
              Row(
                children: [
                  Icon(
                    Icons.medical_services,
                    size: 16,
                    color: theme.textTheme.bodySmall?.color,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      result.doctorName,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),

              // Chief Complaint (if available)
              if (result.chiefComplaint != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.assignment,
                      size: 16,
                      color: theme.textTheme.bodySmall?.color,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        result.chiefComplaint!,
                        style: theme.textTheme.bodySmall,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],

              // Token Number (if available)
              if (result.tokenNumber != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.confirmation_number,
                      size: 16,
                      color: theme.textTheme.bodySmall?.color,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Token #${result.tokenNumber}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
              ],

              // Divider
              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 12),

              // Footer: Match Reason + Relevance + Actions
              Row(
                children: [
                  // Match Reason
                  if (result.matchReason != null)
                    Expanded(
                      child: Row(
                        children: [
                          Icon(
                            Icons.info_outline,
                            size: 14,
                            color: theme.colorScheme.secondary,
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              result.matchReason!,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.secondary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),

                  // Relevance Score
                  _RelevanceIndicator(score: result.relevanceScore),

                  const SizedBox(width: 8),

                  // Quick Actions
                  _QuickActions(result: result),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _onTap(BuildContext context) {
    // TODO: Navigate to appointment details
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Open appointment ${result.id}'),
        duration: const Duration(seconds: 1),
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final tomorrow = today.add(const Duration(days: 1));
    final appointmentDate = DateTime(dateTime.year, dateTime.month, dateTime.day);

    if (appointmentDate == today) {
      return 'Today';
    } else if (appointmentDate == tomorrow) {
      return 'Tomorrow';
    } else if (appointmentDate.isAfter(today) &&
        appointmentDate.isBefore(today.add(const Duration(days: 7)))) {
      return DateFormat('EEEE').format(dateTime); // Day name
    } else {
      return DateFormat('MMM d, yyyy').format(dateTime);
    }
  }

  String _formatTime(DateTime dateTime) {
    return DateFormat('h:mm a').format(dateTime);
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'confirmed':
        return Colors.green;
      case 'scheduled':
        return Colors.blue;
      case 'cancelled':
        return Colors.red;
      case 'no_show':
        return Colors.orange;
      case 'completed':
        return Colors.grey;
      case 'checked_in':
        return Colors.teal;
      case 'in_progress':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }
}

/// Status Badge Widget
class _StatusBadge extends StatelessWidget {
  final String status;
  final String label;
  final String icon;

  const _StatusBadge({
    required this.status,
    required this.label,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _getStatusColor(status).withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: _getStatusColor(status).withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(icon, style: const TextStyle(fontSize: 12)),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: _getStatusColor(status),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'confirmed':
        return Colors.green;
      case 'scheduled':
        return Colors.blue;
      case 'cancelled':
        return Colors.red;
      case 'no_show':
        return Colors.orange;
      case 'completed':
        return Colors.grey;
      case 'checked_in':
        return Colors.teal;
      case 'in_progress':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }
}

/// Relevance Indicator Widget
class _RelevanceIndicator extends StatelessWidget {
  final double score;

  const _RelevanceIndicator({required this.score});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final percentage = (score * 100).toInt();

    return Tooltip(
      message: 'Relevance: $percentage%',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: _getRelevanceColor(score).withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.star,
              size: 12,
              color: _getRelevanceColor(score),
            ),
            const SizedBox(width: 4),
            Text(
              '$percentage%',
              style: theme.textTheme.bodySmall?.copyWith(
                color: _getRelevanceColor(score),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getRelevanceColor(double score) {
    if (score >= 0.8) return Colors.green;
    if (score >= 0.6) return Colors.orange;
    return Colors.grey;
  }
}

/// Quick Actions Widget
class _QuickActions extends StatelessWidget {
  final AppointmentSearchResult result;

  const _QuickActions({required this.result});

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      icon: const Icon(Icons.more_vert, size: 20),
      onSelected: (value) => _handleAction(context, value),
      itemBuilder: (context) => [
        const PopupMenuItem(
          value: 'view',
          child: Row(
            children: [
              Icon(Icons.visibility, size: 18),
              SizedBox(width: 8),
              Text('View Details'),
            ],
          ),
        ),
        if (result.status == 'scheduled' || result.status == 'confirmed')
          const PopupMenuItem(
            value: 'reschedule',
            child: Row(
              children: [
                Icon(Icons.edit_calendar, size: 18),
                SizedBox(width: 8),
                Text('Reschedule'),
              ],
            ),
          ),
        if (result.status == 'scheduled' || result.status == 'confirmed')
          const PopupMenuItem(
            value: 'cancel',
            child: Row(
              children: [
                Icon(Icons.cancel, size: 18, color: Colors.red),
                SizedBox(width: 8),
                Text('Cancel', style: TextStyle(color: Colors.red)),
              ],
            ),
          ),
        const PopupMenuItem(
          value: 'share',
          child: Row(
            children: [
              Icon(Icons.share, size: 18),
              SizedBox(width: 8),
              Text('Share'),
            ],
          ),
        ),
      ],
    );
  }

  void _handleAction(BuildContext context, String action) {
    // TODO: Implement actual actions
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('${action.toUpperCase()}: ${result.id}'),
        duration: const Duration(seconds: 1),
      ),
    );
  }
}
