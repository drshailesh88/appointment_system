import 'package:mocktail/mocktail.dart';
import '../../lib/core/api/api_client.dart';
import '../../lib/core/services/offline_sync_service.dart';
import '../../lib/core/services/websocket_service.dart';
import '../../lib/core/services/background_sync_service.dart';
import '../../lib/core/repositories/appointment_repository.dart';
import '../../lib/core/repositories/patient_repository.dart';
import '../../lib/core/repositories/doctor_repository.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Mock API Client
class MockApiClient extends Mock implements ApiClient {}

/// Mock Offline Sync Service
class MockOfflineSyncService extends Mock implements OfflineSyncService {}

/// Mock WebSocket Service
class MockWebSocketService extends Mock implements WebSocketService {}

/// Mock Background Sync Service
class MockBackgroundSyncService extends Mock implements BackgroundSyncService {}

/// Mock Appointment Repository
class MockAppointmentRepository extends Mock implements AppointmentRepository {}

/// Mock Patient Repository
class MockPatientRepository extends Mock implements PatientRepository {}

/// Mock Doctor Repository
class MockDoctorRepository extends Mock implements DoctorRepository {}

/// Mock Secure Storage
class MockSecureStorage extends Mock implements FlutterSecureStorage {}
