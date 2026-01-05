import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../lib/core/providers/auth_provider.dart';
import '../../lib/core/models/auth_response.dart';
import '../helpers/mock_providers.dart';
import '../helpers/test_data.dart';

void main() {
  late MockApiClient mockApiClient;
  late MockSecureStorage mockStorage;

  setUp(() {
    mockApiClient = MockApiClient();
    mockStorage = MockSecureStorage();

    // Setup default storage responses
    when(() => mockStorage.read(key: any(named: 'key')))
        .thenAnswer((_) async => null);
    when(() => mockStorage.write(key: any(named: 'key'), value: any(named: 'value')))
        .thenAnswer((_) async => {});
    when(() => mockStorage.delete(key: any(named: 'key')))
        .thenAnswer((_) async => {});
  });

  group('AuthProvider', () {
    test('initial state should be unauthenticated', () async {
      final container = ProviderContainer(
        overrides: [
          secureStorageProvider.overrideWithValue(mockStorage),
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      // Wait for initial auth check
      await Future.delayed(const Duration(milliseconds: 100));

      final state = container.read(authStateProvider);

      expect(state.isAuthenticated, false);
      expect(state.isLoading, false);
      expect(state.user, null);
      expect(state.accessToken, null);

      container.dispose();
    });

    test('login should authenticate user', () async {
      final authResponse = AuthResponse.fromJson(TestData.authResponseData);

      when(() => mockApiClient.login(any(), any()))
          .thenAnswer((_) async => authResponse);

      final container = ProviderContainer(
        overrides: [
          secureStorageProvider.overrideWithValue(mockStorage),
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(authStateProvider.notifier);

      await notifier.login('test@example.com', 'password123');

      final state = container.read(authStateProvider);

      expect(state.isAuthenticated, true);
      expect(state.isLoading, false);
      expect(state.accessToken, 'test-access-token');
      expect(state.error, null);

      verify(() => mockApiClient.login('test@example.com', 'password123')).called(1);
      verify(() => mockStorage.write(key: 'access_token', value: 'test-access-token')).called(1);
      verify(() => mockStorage.write(key: 'refresh_token', value: 'test-refresh-token')).called(1);

      container.dispose();
    });

    test('login should handle errors', () async {
      when(() => mockApiClient.login(any(), any()))
          .thenThrow(Exception('Invalid credentials'));

      final container = ProviderContainer(
        overrides: [
          secureStorageProvider.overrideWithValue(mockStorage),
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(authStateProvider.notifier);

      await notifier.login('test@example.com', 'wrongpassword');

      final state = container.read(authStateProvider);

      expect(state.isAuthenticated, false);
      expect(state.isLoading, false);
      expect(state.error, contains('Invalid credentials'));

      container.dispose();
    });

    test('logout should clear authentication', () async {
      final authResponse = AuthResponse.fromJson(TestData.authResponseData);

      when(() => mockApiClient.login(any(), any()))
          .thenAnswer((_) async => authResponse);

      final container = ProviderContainer(
        overrides: [
          secureStorageProvider.overrideWithValue(mockStorage),
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(authStateProvider.notifier);

      // First login
      await notifier.login('test@example.com', 'password123');

      // Then logout
      await notifier.logout();

      final state = container.read(authStateProvider);

      expect(state.isAuthenticated, false);
      expect(state.user, null);
      expect(state.accessToken, null);

      verify(() => mockStorage.delete(key: 'access_token')).called(1);
      verify(() => mockStorage.delete(key: 'refresh_token')).called(1);

      container.dispose();
    });
  });
}
