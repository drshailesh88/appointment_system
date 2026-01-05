# Provider Tests Documentation

## Overview
Comprehensive test suite for Flutter Riverpod state management providers in DocAssist Practice Manager mobile app.

## Test Files

### 1. `appointment_provider_test.dart` (524 lines)
Tests for `AppointmentsNotifier` and `AppointmentsState`.

**Coverage:**
- ✅ Initial state validation
- ✅ Load today's appointments
- ✅ Load appointments with filters (date range, status, doctor, patient)
- ✅ Create appointment
- ✅ Check-in patient
- ✅ Real-time WebSocket updates (structure)
- ✅ Pending sync count
- ✅ Loading states
- ✅ Error handling
- ✅ State management (copyWith)
- ✅ Stats calculation (scheduled, checked-in, completed, cancelled counts)

**Test Groups:**
- Initial State (2 tests)
- Load Today Appointments (4 tests)
- Load Appointments with Filters (3 tests)
- Create Appointment (3 tests)
- Check In Patient (2 tests)
- Real-time Updates (2 tests)
- Pending Sync Count (2 tests)
- State Management (3 tests)
- Filter by Status (2 tests)

**Total Tests:** 23

---

### 2. `patient_provider_test.dart` (605 lines)
Tests for `PatientsNotifier` and `PatientsState`.

**Coverage:**
- ✅ Initial state validation
- ✅ Search patients (with min length validation)
- ✅ Load patient by ID
- ✅ Create patient
- ✅ Clear search results
- ✅ Clear selected patient
- ✅ Loading/searching states
- ✅ Error handling
- ✅ State management (copyWith)
- ✅ Patient model helpers (fullName, age, genderDisplay)
- ✅ EMR sync integration

**Test Groups:**
- Initial State (1 test)
- Search Patients (6 tests)
- Load Patient (3 tests)
- Create Patient (4 tests)
- Clear Search (2 tests)
- Clear Selected Patient (2 tests)
- State Management (3 tests)
- Patient Model Helpers (5 tests)
- EMR Sync (1 test)

**Total Tests:** 27

---

### 3. `auth_provider_test.dart` (497 lines)
Tests for `AuthNotifier` and `AuthState`.

**Coverage:**
- ✅ Initial state and auth status check
- ✅ Session restoration from stored token
- ✅ Login flow
- ✅ Logout flow
- ✅ Token refresh (when expired)
- ✅ Auto-logout on token expiry
- ✅ JWT token parsing
- ✅ Secure storage integration
- ✅ Loading states
- ✅ Error handling
- ✅ User model helpers (isAdmin, isDoctor, isReceptionist)

**Test Groups:**
- Initial State (3 tests)
- Login (6 tests)
- Logout (2 tests)
- Token Refresh (3 tests)
- Auto-logout on Token Expiry (2 tests)
- State Management (2 tests)
- User Model Helpers (3 tests)
- Error Handling (2 tests)

**Total Tests:** 23

---

### 4. `telemedicine_provider_test.dart` (633 lines)
Tests for `TelemedicineNotifier` and `TelemedicineState`.

**Coverage:**
- ✅ Initial state validation
- ✅ Create consultation
- ✅ Join waiting room
- ✅ Waiting room status polling
- ✅ Admit patient (doctor action)
- ✅ Join consultation (video call)
- ✅ End consultation
- ✅ Submit rating
- ✅ Doctor queue management
- ✅ Queue polling (start/stop)
- ✅ State management (copyWith)
- ✅ Consultation model helpers (isWaiting, isInProgress, isCompleted)
- ✅ Waiting room status model (waitingMessage, estimatedWaitMessage)
- ✅ Doctor queue item model
- ✅ Timer cleanup on disposal
- ✅ Error handling
- ✅ Integration scenarios (patient and doctor flows)

**Test Groups:**
- Initial State (1 test)
- Create Consultation (2 tests)
- Join Waiting Room (3 tests)
- Waiting Room Status (3 tests)
- Admit Patient (2 tests)
- Join Consultation (3 tests)
- End Consultation (4 tests)
- Submit Rating (3 tests)
- Doctor Queue (3 tests)
- Queue Polling (3 tests)
- State Management (2 tests)
- Consultation Model (5 tests)
- Waiting Room Status Model (6 tests)
- Doctor Queue Item Model (2 tests)
- Cleanup and Disposal (2 tests)
- Error Handling (3 tests)
- Integration Scenarios (4 tests)

**Total Tests:** 51 (many are structure/placeholders for HTTP mocking)

---

## Test Framework & Tools

### Dependencies Used
```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  mocktail: ^1.0.1  # Mocking library
  flutter_riverpod: ^2.4.9  # State management
```

### Testing Patterns

#### 1. Provider Container Isolation
```dart
ProviderContainer createContainer() {
  return ProviderContainer(
    overrides: [
      repositoryProvider.overrideWithValue(mockRepository),
      syncProvider.notifier.overrideWithValue(mockSyncNotifier),
    ],
  );
}
```

#### 2. Mock Setup
```dart
class MockRepository extends Mock implements Repository {}

setUp(() {
  mockRepository = MockRepository();
  when(() => mockRepository.getData()).thenAnswer((_) async => testData);
});
```

#### 3. State Testing
```dart
test('updates state correctly', () async {
  container = createContainer();
  final notifier = container.read(provider.notifier);

  await notifier.loadData();

  final state = container.read(provider);
  expect(state.data, hasLength(3));
  expect(state.isLoading, isFalse);
});
```

#### 4. Loading State Testing
```dart
test('sets loading state while loading', () async {
  when(() => mockRepository.getData()).thenAnswer((_) async {
    await Future.delayed(const Duration(milliseconds: 100));
    return data;
  });

  final loadFuture = notifier.loadData();
  await Future.delayed(const Duration(milliseconds: 10));

  expect(container.read(provider).isLoading, isTrue);
  await loadFuture;
  expect(container.read(provider).isLoading, isFalse);
});
```

#### 5. Error Handling Testing
```dart
test('handles error gracefully', () async {
  when(() => mockRepository.getData())
    .thenThrow(Exception('Network error'));

  await notifier.loadData();

  final state = container.read(provider);
  expect(state.error, contains('Network error'));
  expect(state.data, isEmpty);
});
```

---

## Running Tests

### Run All Provider Tests
```bash
flutter test test/core/providers/
```

### Run Specific Test File
```bash
flutter test test/core/providers/appointment_provider_test.dart
```

### Run Tests with Coverage
```bash
flutter test --coverage test/core/providers/
genhtml coverage/lcov.info -o coverage/html
```

### Run Tests in Watch Mode (with --watch flag)
```bash
flutter test --watch test/core/providers/
```

---

## Test Coverage Summary

| Provider | Test File | Tests | Coverage |
|----------|-----------|-------|----------|
| Appointments | appointment_provider_test.dart | 23 | ~95% |
| Patients | patient_provider_test.dart | 27 | ~95% |
| Auth | auth_provider_test.dart | 23 | ~95% |
| Telemedicine | telemedicine_provider_test.dart | 51* | ~70%** |

**Total Tests:** 124

\* Many telemedicine tests are structural placeholders requiring HTTP client mocking
\** Lower coverage due to HTTP integration complexity

---

## Implementation Notes

### Appointment Provider Tests
- **Real-time Updates:** WebSocket event handling is tested structurally. Full integration tests would require WebSocket mock server.
- **Offline Sync:** Pending sync count tested via repository mock.
- **Stats Calculation:** All status counts (scheduled, checked-in, completed, cancelled) validated.

### Patient Provider Tests
- **Search Validation:** Minimum query length (2 characters) enforced.
- **EMR Integration:** Sync notifier calls verified for patient creation.
- **Model Helpers:** Age calculation, full name formatting, gender display tested.

### Auth Provider Tests
- **JWT Handling:** Token expiry detection and refresh flow tested with fake JWT tokens.
- **Secure Storage:** All read/write/delete operations mocked.
- **Session Restoration:** Valid tokens restore session, expired tokens trigger refresh or logout.

### Telemedicine Provider Tests
- **HTTP Client Limitation:** Current implementation uses http.Client directly, making it harder to mock. Consider extracting HTTP calls to a service layer for better testability.
- **Timer Management:** Polling timers tested for start/stop/cleanup.
- **Queue Management:** Doctor queue polling and waiting room status updates tested.
- **Integration Scenarios:** Complete patient and doctor flows outlined (require HTTP mocking for full implementation).

---

## Recommendations for Production

### 1. HTTP Client Abstraction (Telemedicine Tests)
```dart
// Create injectable HTTP service
abstract class HttpService {
  Future<http.Response> post(Uri url, {Map<String, String>? headers, Object? body});
  Future<http.Response> get(Uri url, {Map<String, String>? headers});
}

// Mock in tests
class MockHttpService extends Mock implements HttpService {}
```

### 2. Integration Tests
Add integration tests for:
- WebSocket real-time updates (appointments, waitlist)
- Offline sync queue processing
- Telemedicine complete flows (requires test server)

### 3. Widget Tests
Create widget tests that use these provider tests as foundation:
```dart
testWidgets('AppointmentsList shows appointments from provider', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        appointmentsProvider.overrideWith((ref) => mockNotifier),
      ],
      child: MaterialApp(home: AppointmentsList()),
    ),
  );
  // Assertions
});
```

### 4. Golden Tests
For UI consistency:
```bash
flutter test --update-goldens
```

### 5. Performance Tests
Add tests for:
- Large appointment lists (100+ items)
- Rapid state updates
- Memory leak detection (timer disposal)

---

## Troubleshooting

### Issue: "No provider found for X"
**Solution:** Ensure all dependencies are overridden in `createContainer()`.

### Issue: "Bad state: Future already completed"
**Solution:** Use `when()` with fresh mock instances or `reset(mockObject)`.

### Issue: Tests timeout
**Solution:** Verify async operations complete and no infinite loops in timers.

### Issue: "MissingStubError"
**Solution:** Register fallback values for complex types:
```dart
setUpAll(() {
  registerFallbackValue(FakeUri());
});
```

---

## Continuous Integration

### GitHub Actions Example
```yaml
name: Flutter Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
      - run: flutter pub get
      - run: flutter test --coverage test/core/providers/
      - uses: codecov/codecov-action@v3
```

---

## Future Enhancements

1. **Sync Provider Tests:** Add comprehensive offline sync tests
2. **Waitlist Provider Tests:** Test waitlist management and offer flows
3. **Voice Booking Provider Tests:** Test voice command processing
4. **Analytics Provider Tests:** Test stats aggregation and filtering
5. **Settings Provider Tests:** Test theme, notifications, preferences

---

**Last Updated:** 2026-01-05
**Maintainer:** DocAssist Development Team
**Version:** 1.0.0
