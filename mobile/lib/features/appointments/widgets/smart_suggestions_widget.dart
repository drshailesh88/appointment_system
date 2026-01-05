import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/providers/smart_scheduling_provider.dart';

/// Widget displaying AI-powered smart appointment slot suggestions
///
/// Shows suggested slots with confidence scores and reasons, allowing
/// one-tap booking from the suggestions.
class SmartSuggestionsWidget extends ConsumerStatefulWidget {
  final String patientId;
  final String doctorId;
  final String appointmentType;
  final int durationMinutes;
  final VoidCallback? onRefresh;
  final Function(DateTime slotTime)? onSlotSelected;

  const SmartSuggestionsWidget({
    Key? key,
    required this.patientId,
    required this.doctorId,
    this.appointmentType = 'new_consultation',
    this.durationMinutes = 15,
    this.onRefresh,
    this.onSlotSelected,
  }) : super(key: key);

  @override
  ConsumerState<SmartSuggestionsWidget> createState() =>
      _SmartSuggestionsWidgetState();
}

class _SmartSuggestionsWidgetState
    extends ConsumerState<SmartSuggestionsWidget> {
  @override
  void initState() {
    super.initState();
    // Load suggestions when widget is initialized
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadSuggestions();
    });
  }

  void _loadSuggestions() {
    ref.read(smartSchedulingProvider.notifier).loadSuggestions(
          patientId: widget.patientId,
          doctorId: widget.doctorId,
          appointmentType: widget.appointmentType,
          durationMinutes: widget.durationMinutes,
          maxSuggestions: 5,
        );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(smartSchedulingProvider);

    return Card(
      elevation: 2,
      margin: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Icon(
                  Icons.lightbulb_outline,
                  color: Colors.amber,
                  size: 24,
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Smart Suggestions',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'AI-powered optimal time slots',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: state.isLoading
                      ? null
                      : () {
                          _loadSuggestions();
                          widget.onRefresh?.call();
                        },
                  tooltip: 'Refresh suggestions',
                ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Content
          if (state.isLoading)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(
                child: Column(
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text(
                      'Analyzing patterns...',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            )
          else if (state.error != null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Icon(
                    Icons.error_outline,
                    color: Colors.red,
                    size: 48,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    state.error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.red),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _loadSuggestions,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Try Again'),
                  ),
                ],
              ),
            )
          else if (state.suggestions.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(
                child: Column(
                  children: [
                    Icon(
                      Icons.event_busy,
                      color: Colors.grey,
                      size: 48,
                    ),
                    SizedBox(height: 8),
                    Text(
                      'No suggestions available',
                      style: TextStyle(color: Colors.grey),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Try selecting a different date',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: state.suggestions.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final suggestion = state.suggestions[index];
                return _SuggestionTile(
                  suggestion: suggestion,
                  onTap: () {
                    widget.onSlotSelected?.call(suggestion.slotTime);
                    _submitFeedback(suggestion, wasAccepted: true);
                  },
                );
              },
            ),
        ],
      ),
    );
  }

  void _submitFeedback(SlotSuggestion suggestion, {required bool wasAccepted}) {
    // Submit feedback asynchronously (fire and forget)
    ref.read(smartSchedulingProvider.notifier).submitFeedback(
          patientId: widget.patientId,
          doctorId: widget.doctorId,
          suggestedSlot: suggestion.slotTime,
          wasAccepted: wasAccepted,
        );
  }
}

/// Individual suggestion tile
class _SuggestionTile extends StatelessWidget {
  final SlotSuggestion suggestion;
  final VoidCallback onTap;

  const _SuggestionTile({
    required this.suggestion,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('EEE, MMM d');
    final timeFormat = DateFormat('h:mm a');

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 8,
      ),
      leading: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _ConfidenceBadge(score: suggestion.score),
        ],
      ),
      title: Text(
        '${dateFormat.format(suggestion.slotTime)} at ${timeFormat.format(suggestion.slotTime)}',
        style: const TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 16,
        ),
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 4),
          Text(
            suggestion.confidenceLevel,
            style: TextStyle(
              fontSize: 12,
              color: _getConfidenceColor(suggestion.score),
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          ...suggestion.reasons.take(2).map(
                (reason) => Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.check_circle,
                        size: 12,
                        color: Colors.green,
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          reason,
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.grey,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ),
      trailing: ElevatedButton(
        onPressed: onTap,
        style: ElevatedButton.styleFrom(
          backgroundColor: Theme.of(context).primaryColor,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 8,
          ),
        ),
        child: const Text('Book'),
      ),
    );
  }

  static Color _getConfidenceColor(double score) {
    if (score >= 80) return Colors.green;
    if (score >= 60) return Colors.blue;
    if (score >= 40) return Colors.orange;
    return Colors.grey;
  }
}

/// Confidence score badge
class _ConfidenceBadge extends StatelessWidget {
  final double score;

  const _ConfidenceBadge({required this.score});

  @override
  Widget build(BuildContext context) {
    final color = _getColor();
    final percentage = score.toInt();

    return Container(
      width: 50,
      height: 50,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color.withOpacity(0.1),
        border: Border.all(
          color: color,
          width: 2,
        ),
      ),
      child: Center(
        child: Text(
          '$percentage%',
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.bold,
            fontSize: 12,
          ),
        ),
      ),
    );
  }

  Color _getColor() {
    if (score >= 80) return Colors.green;
    if (score >= 60) return Colors.blue;
    if (score >= 40) return Colors.orange;
    return Colors.grey;
  }
}

/// Compact version for inline suggestions
class SmartSuggestionsCompact extends ConsumerWidget {
  final String patientId;
  final String doctorId;
  final String appointmentType;
  final int durationMinutes;
  final Function(DateTime slotTime)? onSlotSelected;

  const SmartSuggestionsCompact({
    Key? key,
    required this.patientId,
    required this.doctorId,
    this.appointmentType = 'new_consultation',
    this.durationMinutes = 15,
    this.onSlotSelected,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Use the auto-suggestions provider for automatic loading
    final suggestionsAsync = ref.watch(
      autoSuggestionsProvider({
        'patientId': patientId,
        'doctorId': doctorId,
        'appointmentType': appointmentType,
        'durationMinutes': durationMinutes.toString(),
        'maxSuggestions': '3',
      }),
    );

    return suggestionsAsync.when(
      data: (suggestions) {
        if (suggestions.isEmpty) {
          return const SizedBox.shrink();
        }

        final timeFormat = DateFormat('EEE h:mm a');

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.lightbulb_outline, size: 16, color: Colors.amber),
                SizedBox(width: 4),
                Text(
                  'Suggested times:',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: suggestions.map((suggestion) {
                return ActionChip(
                  avatar: CircleAvatar(
                    backgroundColor: _getConfidenceColor(suggestion.score),
                    child: Text(
                      '${suggestion.score.toInt()}',
                      style: const TextStyle(
                        fontSize: 10,
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  label: Text(
                    timeFormat.format(suggestion.slotTime),
                    style: const TextStyle(fontSize: 12),
                  ),
                  onPressed: () {
                    onSlotSelected?.call(suggestion.slotTime);
                  },
                );
              }).toList(),
            ),
          ],
        );
      },
      loading: () => const Center(
        child: Padding(
          padding: EdgeInsets.all(8.0),
          child: SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      ),
      error: (error, stack) => const SizedBox.shrink(),
    );
  }

  static Color _getConfidenceColor(double score) {
    if (score >= 80) return Colors.green;
    if (score >= 60) return Colors.blue;
    if (score >= 40) return Colors.orange;
    return Colors.grey;
  }
}
