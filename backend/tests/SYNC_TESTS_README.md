# Offline Sync Tests - DocAssist Practice Manager

## Overview

Comprehensive offline sync tests have been created to validate the sync functionality of the DocAssist Practice Manager application. These tests cover both backend API sync operations and Flutter mobile client sync services.

## Files Created

### Backend Tests

1. **`tests/test_sync.py`** (Full test suite - 900+ lines)
   - Comprehensive test suite with all scenarios
   - Uses class-based organization
   - Requires some fixture adjustments to work with existing conftest

2. **`tests/test_sync_simple.py`** (Simplified version - 600+ lines)
   - Simplified, function-based tests
   - Easier to debug and maintain
   - Uses existing conftest fixtures directly

### Mobile Tests

3. **`mobile/test/sync_test.dart`** (600+ lines)
   - Tests for `OfflineSyncService`
   - Tests for `BackgroundSyncService`
   - Tests for sync state management
   - Mock-based unit tests

### Infrastructure Fixes

4. **`app/models/types.py`**
   - Custom JSONB type for cross-database compatibility
   - Allows models to use JSONB with PostgreSQL while supporting SQLite for testing
   - Fixes: `AttributeError: 'SQLiteTypeCompiler' object has no attribute 'visit_JSONB'`

## Test Coverage

### A. Basic Sync Operations ✓
- Sync pull with empty changes
- Sync push (create new appointment)
- Full sync for initial device setup
- Incremental sync with delta updates
- Sync with empty changes

### B. Conflict Resolution ✓
- Server wins (older client data)
- Client wins (newer client data)
- Concurrent updates from multiple devices
- Delete conflicts (deleted on server, modified on client)
- Last-write-wins strategy

### C. Offline Queue Management ✓
- Queue operations when offline
- Process queue when online
- Queue persistence across app restart
- Queue ordering (FIFO)
- Failed operation retry with exponential backoff

### D. Data Integrity ✓
- No data loss during sync
- No duplicate records
- Referential integrity (patient → appointment)
- Timestamp accuracy
- Version tracking

### E. Network Conditions ✓
- Sync with slow network (simulated)
- Sync interrupted mid-transfer
- Partial sync recovery
- Timeout handling
- Retry logic with backoff

### F. Edge Cases ✓
- Very large sync payload (100+ items)
- Sync with deleted user
- Sync across timezone change
- Unicode data sync (Hindi, Chinese characters)
- Binary data considerations

### G. Multi-Device Sync ✓
- Same user, multiple devices
- Sync ordering across devices
- Device token management

### H. Integration Tests ✓
- Complete offline → online workflow
- Bidirectional sync (push + pull)
- Full sync cycle validation

## Issues Found & Fixed

### 1. JSONB Type Compatibility ✅ FIXED
**Problem**: SQLite doesn't support PostgreSQL's JSONB type, causing tests to fail.

**Solution**: Created `app/models/types.py` with a custom JSONB type that:
- Uses JSONB for PostgreSQL (production)
- Falls back to JSON for SQLite (testing)

**Models Updated**:
- `app/models/doctor.py`
- `app/models/appointment.py`
- `app/models/payment.py`
- `app/models/calendar_sync.py`
- `app/models/noshow_prediction.py`
- `app/models/lab_result.py`

### 2. Missing Dependencies ✅ FIXED
- Installed `aiosqlite` for async SQLite support
- Installed `email-validator` for Pydantic email validation

### 3. Test Infrastructure Issues ⚠️ IN PROGRESS
**Problem**: Tests are timing out during async setup/teardown.

**Possible Causes**:
- Async fixture lifecycle issues
- Database connection pool not closing properly
- Circular dependencies in model imports
- Long-running migrations or table creation

**Recommendations**:
1. Review async fixture scoping in `conftest.py`
2. Add explicit cleanup in fixture teardown
3. Use `pytest-timeout` plugin for better timeout management
4. Consider using `pytest-xdist` for parallel test execution

## Test Execution

### Backend Tests (Python/Pytest)

```bash
# Run all sync tests
cd backend
pytest tests/test_sync_simple.py -v

# Run specific test category
pytest tests/test_sync_simple.py::test_sync_pull_empty_changes -v

# Run with coverage
pytest tests/test_sync_simple.py --cov=app/api --cov=app/services

# Run with timeout
pytest tests/test_sync_simple.py --timeout=30 -v
```

### Mobile Tests (Flutter/Dart)

```bash
# Run all sync tests
cd mobile
flutter test test/sync_test.dart

# Run with coverage
flutter test --coverage test/sync_test.dart
flutter pub global activate coverage
genhtml coverage/lcov.info -o coverage/html

# Run specific test
flutter test test/sync_test.dart --name "should queue sync item when offline"
```

## Sync Architecture

### Mobile Client

```
User Action
    ↓
Repository Layer (offline-first)
    ↓
OfflineSyncService / BackgroundSyncService
    ↓
Queue Manager (Hive/SharedPreferences)
    ↓
API Client (when online)
    ↓
Backend API
```

### Backend API

```
HTTP Request
    ↓
FastAPI Route
    ↓
Pydantic Validation
    ↓
Business Logic
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL Database
```

### Conflict Resolution Strategy

**Current Implementation**: Last-Write-Wins (LWW)
- Simple and predictable
- No version tracking required
- May lose data in concurrent updates

**Future Enhancement**: Operational Transformation (OT)
- Track field-level changes
- Merge non-conflicting updates
- Show conflict dialog for true conflicts

## Sync Queue Structure

```dart
class SyncQueueItem {
  String id;                    // Unique queue item ID
  String entityType;            // 'appointment', 'patient', 'waitlist'
  String entityId;              // Entity's UUID
  SyncOperation operation;      // create, update, delete
  Map<String, dynamic> data;    // Entity data
  DateTime createdAt;           // Queue timestamp
  int retryCount;               // Retry attempts
  String? errorMessage;         // Last error
  SyncStatus status;            // pending, syncing, completed, failed
}
```

## Performance Benchmarks

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Queue item | < 10ms | TBD | - |
| Sync 10 items | < 1s | TBD | - |
| Sync 100 items | < 5s | TBD | - |
| Full sync (500 items) | < 10s | TBD | - |
| Conflict resolution | < 100ms | TBD | - |

## Known Limitations

1. **No Version Tracking**: Current implementation doesn't track entity versions, relying on last-write-wins.

2. **No Partial Field Sync**: Updates sync entire entities, not individual fields.

3. **No Conflict Visualization**: Users aren't shown what data was overwritten during conflicts.

4. **Limited Offline Storage**: Mobile devices have storage limits (recommend < 10,000 queued items).

5. **No Delta Compression**: Large entities are synced in full, not as deltas.

## Future Enhancements

### Phase 1: Improved Conflict Resolution
- [ ] Add version tracking to entities (`version` field)
- [ ] Implement optimistic locking
- [ ] Show conflict dialog to users

### Phase 2: Intelligent Sync
- [ ] Delta sync (only changed fields)
- [ ] Compression for large payloads
- [ ] Batch sync with transaction support

### Phase 3: Advanced Features
- [ ] Real-time sync via WebSocket
- [ ] Peer-to-peer sync between devices
- [ ] Sync priority queue (urgent items first)

## Testing Checklist

- [x] Create backend sync tests
- [x] Create mobile sync tests
- [x] Fix JSONB compatibility issues
- [ ] Run and debug tests (timing out)
- [ ] Measure performance benchmarks
- [ ] Test with real network conditions
- [ ] Test with large datasets (1000+ items)
- [ ] Test concurrent multi-device scenarios
- [ ] Load testing with multiple clients

## Contributing

When adding sync-related code:

1. **Always test offline-first**: Assume network is unavailable
2. **Add retry logic**: Network failures are common
3. **Validate data**: Don't trust client data
4. **Log sync events**: Essential for debugging
5. **Update tests**: Add test cases for new sync scenarios

## References

- Backend Sync Code: `backend/app/api/v1/appointments.py`
- Mobile Sync Services: `mobile/lib/core/services/`
- Sync State Management: `mobile/lib/core/providers/sync_provider.dart`
- Repository Pattern: `mobile/lib/core/repositories/`

## Contact

For questions about sync implementation:
- Check `CLAUDE.md` for project overview
- Review existing sync services
- Run tests to understand behavior
