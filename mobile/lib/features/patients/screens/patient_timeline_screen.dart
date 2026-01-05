import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/timeline_event.dart';
import '../../../core/models/visit.dart';
import '../../../core/models/procedure.dart';
import '../widgets/timeline_card.dart';
import '../widgets/visit_summary_card.dart';
import '../widgets/procedure_card.dart';
import '../providers/timeline_provider.dart';

/// Patient timeline screen showing chronological view of patient history
class PatientTimelineScreen extends ConsumerStatefulWidget {
  final String patientId;
  final String patientName;

  const PatientTimelineScreen({
    super.key,
    required this.patientId,
    required this.patientName,
  });

  @override
  ConsumerState<PatientTimelineScreen> createState() => _PatientTimelineScreenState();
}

class _PatientTimelineScreenState extends ConsumerState<PatientTimelineScreen> {
  final Set<TimelineEventType> _selectedFilters = {
    TimelineEventType.appointment,
    TimelineEventType.visit,
    TimelineEventType.procedure,
    TimelineEventType.document,
  };

  DateTimeRange? _dateRange;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(timelineProvider(widget.patientId).notifier).loadTimeline();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(timelineProvider(widget.patientId));

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Patient Timeline'),
            Text(
              widget.patientName,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.white70,
                  ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
          IconButton(
            icon: const Icon(Icons.date_range),
            onPressed: _showDateRangePicker,
          ),
        ],
      ),
      body: Column(
        children: [
          // Active filters display
          if (_selectedFilters.length < 4 || _dateRange != null)
            _ActiveFiltersBar(),

          // Timeline content
          Expanded(
            child: _buildContent(state),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(TimelineState state) {
    if (state.isLoading && state.events.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: Colors.red[300],
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading timeline',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                ref.read(timelineProvider(widget.patientId).notifier).loadTimeline();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final filteredEvents = _filterEvents(state.events);

    if (filteredEvents.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.timeline,
              size: 64,
              color: Colors.grey[300],
            ),
            const SizedBox(height: 16),
            Text(
              'No timeline events',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Timeline events will appear here',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(timelineProvider(widget.patientId).notifier).loadTimeline();
      },
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: filteredEvents.length,
        itemBuilder: (context, index) {
          final event = filteredEvents[index];
          final isLast = index == filteredEvents.length - 1;

          return TimelineCard(
            event: event,
            showConnector: !isLast,
            onTap: () => _handleEventTap(event, state),
          );
        },
      ),
    );
  }

  List<TimelineEvent> _filterEvents(List<TimelineEvent> events) {
    return events.where((event) {
      // Filter by type
      if (!_selectedFilters.contains(event.type)) {
        return false;
      }

      // Filter by date range
      if (_dateRange != null) {
        if (event.date.isBefore(_dateRange!.start) ||
            event.date.isAfter(_dateRange!.end.add(const Duration(days: 1)))) {
          return false;
        }
      }

      return true;
    }).toList();
  }

  void _handleEventTap(TimelineEvent event, TimelineState state) {
    switch (event.type) {
      case TimelineEventType.visit:
        final visit = state.visits.firstWhere(
          (v) => v.id == event.id,
          orElse: () => throw Exception('Visit not found'),
        );
        _showVisitDetails(visit);
        break;
      case TimelineEventType.procedure:
        final procedure = state.procedures.firstWhere(
          (p) => p.id == event.id,
          orElse: () => throw Exception('Procedure not found'),
        );
        _showProcedureDetails(procedure);
        break;
      case TimelineEventType.appointment:
      case TimelineEventType.document:
        // TODO: Navigate to respective detail screens
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${event.typeDisplay} details coming soon')),
        );
        break;
    }
  }

  void _showVisitDetails(Visit visit) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        minChildSize: 0.5,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: VisitSummaryCard(visit: visit),
          ),
        ),
      ),
    );
  }

  void _showProcedureDetails(Procedure procedure) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        minChildSize: 0.5,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: ProcedureCard(procedure: procedure),
          ),
        ),
      ),
    );
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Filter Timeline'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: TimelineEventType.values.map((type) {
              return CheckboxListTile(
                title: Text(_getTypeLabel(type)),
                value: _selectedFilters.contains(type),
                onChanged: (value) {
                  setDialogState(() {
                    if (value == true) {
                      _selectedFilters.add(type);
                    } else {
                      _selectedFilters.remove(type);
                    }
                  });
                },
              );
            }).toList(),
          ),
          actions: [
            TextButton(
              onPressed: () {
                setDialogState(() {
                  _selectedFilters.clear();
                  _selectedFilters.addAll(TimelineEventType.values);
                });
              },
              child: const Text('Select All'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                setState(() {});
                Navigator.pop(context);
              },
              child: const Text('Apply'),
            ),
          ],
        ),
      ),
    );
  }

  void _showDateRangePicker() async {
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
      initialDateRange: _dateRange,
    );

    if (picked != null) {
      setState(() {
        _dateRange = picked;
      });
    }
  }

  String _getTypeLabel(TimelineEventType type) {
    switch (type) {
      case TimelineEventType.appointment:
        return 'Appointments';
      case TimelineEventType.visit:
        return 'Visits';
      case TimelineEventType.procedure:
        return 'Procedures';
      case TimelineEventType.document:
        return 'Documents';
    }
  }

  Widget _ActiveFiltersBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: Colors.grey[100],
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          if (_selectedFilters.length < 4)
            ..._selectedFilters.map((type) => Chip(
                  label: Text(_getTypeLabel(type)),
                  onDeleted: () {
                    setState(() {
                      _selectedFilters.remove(type);
                    });
                  },
                  deleteIconColor: Colors.grey[600],
                )),
          if (_dateRange != null)
            Chip(
              label: Text(
                '${_dateRange!.start.toString().split(' ')[0]} - ${_dateRange!.end.toString().split(' ')[0]}',
              ),
              onDeleted: () {
                setState(() {
                  _dateRange = null;
                });
              },
              deleteIconColor: Colors.grey[600],
            ),
        ],
      ),
    );
  }
}
