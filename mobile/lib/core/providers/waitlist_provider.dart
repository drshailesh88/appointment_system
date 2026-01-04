import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

// Waitlist Priority enum
enum WaitlistPriority {
  emergency,
  urgent,
  normal,
  flexible;

  String get displayName {
    switch (this) {
      case WaitlistPriority.emergency:
        return 'Emergency';
      case WaitlistPriority.urgent:
        return 'Urgent';
      case WaitlistPriority.normal:
        return 'Normal';
      case WaitlistPriority.flexible:
        return 'Flexible';
    }
  }
}

// Waitlist Status enum
enum WaitlistStatus {
  waiting,
  offered,
  confirmed,
  expired,
  cancelled;

  String get displayName {
    switch (this) {
      case WaitlistStatus.waiting:
        return 'Waiting';
      case WaitlistStatus.offered:
        return 'Slot Offered';
      case WaitlistStatus.confirmed:
        return 'Confirmed';
      case WaitlistStatus.expired:
        return 'Expired';
      case WaitlistStatus.cancelled:
        return 'Cancelled';
    }
  }
}

// Waitlist Entry Model
class WaitlistEntry {
  final String id;
  final String patientId;
  final String patientName;
  final String? doctorId;
  final String? doctorName;
  final String? preferredDate;
  final String? preferredTimeSlot;
  final WaitlistPriority priority;
  final WaitlistStatus status;
  final int queuePosition;
  final String? notes;
  final DateTime createdAt;
  final DateTime? expiresAt;

  WaitlistEntry({
    required this.id,
    required this.patientId,
    required this.patientName,
    this.doctorId,
    this.doctorName,
    this.preferredDate,
    this.preferredTimeSlot,
    required this.priority,
    required this.status,
    required this.queuePosition,
    this.notes,
    required this.createdAt,
    this.expiresAt,
  });

  factory WaitlistEntry.fromJson(Map<String, dynamic> json) {
    return WaitlistEntry(
      id: json['id'] ?? '',
      patientId: json['patient_id'] ?? '',
      patientName: json['patient_name'] ?? 'Unknown',
      doctorId: json['doctor_id'],
      doctorName: json['doctor_name'],
      preferredDate: json['preferred_date'],
      preferredTimeSlot: json['preferred_time_slot'],
      priority: _parsePriority(json['priority']),
      status: _parseStatus(json['status']),
      queuePosition: json['queue_position'] ?? 0,
      notes: json['notes'],
      createdAt: DateTime.parse(json['created_at']),
      expiresAt: json['slot_offer_expires_at'] != null
          ? DateTime.parse(json['slot_offer_expires_at'])
          : null,
    );
  }

  static WaitlistPriority _parsePriority(String? priority) {
    switch (priority) {
      case 'emergency':
        return WaitlistPriority.emergency;
      case 'urgent':
        return WaitlistPriority.urgent;
      case 'flexible':
        return WaitlistPriority.flexible;
      default:
        return WaitlistPriority.normal;
    }
  }

  static WaitlistStatus _parseStatus(String? status) {
    switch (status) {
      case 'offered':
        return WaitlistStatus.offered;
      case 'confirmed':
        return WaitlistStatus.confirmed;
      case 'expired':
        return WaitlistStatus.expired;
      case 'cancelled':
        return WaitlistStatus.cancelled;
      default:
        return WaitlistStatus.waiting;
    }
  }

  bool get hasActiveOffer =>
      status == WaitlistStatus.offered &&
      expiresAt != null &&
      expiresAt!.isAfter(DateTime.now());
}

// Waitlist State
class WaitlistState {
  final bool isLoading;
  final String? error;
  final List<WaitlistEntry> entries;
  final WaitlistEntry? selectedEntry;

  const WaitlistState({
    this.isLoading = false,
    this.error,
    this.entries = const [],
    this.selectedEntry,
  });

  WaitlistState copyWith({
    bool? isLoading,
    String? error,
    List<WaitlistEntry>? entries,
    WaitlistEntry? selectedEntry,
  }) {
    return WaitlistState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      entries: entries ?? this.entries,
      selectedEntry: selectedEntry ?? this.selectedEntry,
    );
  }

  List<WaitlistEntry> get waitingEntries =>
      entries.where((e) => e.status == WaitlistStatus.waiting).toList();

  List<WaitlistEntry> get offeredEntries =>
      entries.where((e) => e.status == WaitlistStatus.offered).toList();

  List<WaitlistEntry> get emergencyEntries =>
      entries.where((e) => e.priority == WaitlistPriority.emergency).toList();
}

// Waitlist Notifier
class WaitlistNotifier extends StateNotifier<WaitlistState> {
  final ApiClient _apiClient;

  WaitlistNotifier(this._apiClient) : super(const WaitlistState());

  Future<void> loadWaitlist({String? doctorId, String? status}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      String url = '/waitlist';
      final params = <String>[];
      if (doctorId != null) params.add('doctor_id=$doctorId');
      if (status != null) params.add('status=$status');
      if (params.isNotEmpty) url += '?${params.join('&')}';

      final response = await _apiClient.get(url);

      if (response != null) {
        final entries = (response as List<dynamic>)
            .map((e) => WaitlistEntry.fromJson(e))
            .toList();
        state = state.copyWith(isLoading: false, entries: entries);
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<bool> addToWaitlist({
    required String patientId,
    String? doctorId,
    String? preferredDate,
    String? preferredTimeSlot,
    String priority = 'normal',
    String? notes,
  }) async {
    try {
      final response = await _apiClient.post('/waitlist', {
        'patient_id': patientId,
        if (doctorId != null) 'doctor_id': doctorId,
        if (preferredDate != null) 'preferred_date': preferredDate,
        if (preferredTimeSlot != null) 'preferred_time_slot': preferredTimeSlot,
        'priority': priority,
        if (notes != null) 'notes': notes,
      });

      if (response != null) {
        await loadWaitlist();
        return true;
      }
      return false;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> confirmSlot(String entryId) async {
    try {
      final response = await _apiClient.post('/waitlist/$entryId/confirm', {});

      if (response != null) {
        await loadWaitlist();
        return true;
      }
      return false;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> declineSlot(String entryId) async {
    try {
      final response = await _apiClient.post('/waitlist/$entryId/decline', {});

      if (response != null) {
        await loadWaitlist();
        return true;
      }
      return false;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> cancelEntry(String entryId) async {
    try {
      await _apiClient.delete('/waitlist/$entryId');
      await loadWaitlist();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> updatePriority(String entryId, String priority) async {
    try {
      final response = await _apiClient.put('/waitlist/$entryId', {
        'priority': priority,
      });

      if (response != null) {
        await loadWaitlist();
        return true;
      }
      return false;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }
}

// Provider
final waitlistProvider =
    StateNotifierProvider<WaitlistNotifier, WaitlistState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WaitlistNotifier(apiClient);
});
