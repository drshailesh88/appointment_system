import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/core/api/api_client.dart';
import 'package:docassist_mobile/core/models/auth_response.dart';
import 'package:docassist_mobile/core/models/user.dart';
import 'package:docassist_mobile/core/providers/auth_provider.dart';

// Mock classes
class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

class MockApiClient extends Mock implements ApiClient {}

// Fake JWT tokens for testing
const _fakeAccessToken =
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwicm9sZSI6ImRvY3RvciIsImNsaW5pY19pZCI6ImNsaW5pYzEiLCJleHAiOjk5OTk5OTk5OTl9.fake';
const _fakeRefreshToken = 'refresh_token_123';

// Expired token (exp: 1000000000 = Sep 2001)
const _expiredAccessToken =
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwicm9sZSI6ImRvY3RvciIsImNsaW5pY19pZCI6ImNsaW5pYzEiLCJleHAiOjEwMDAwMDAwMDB9.fake';

void main() {
  late MockFlutterSecureStorage mockStorage;
  late MockApiClient mockApiClient;
  late ProviderContainer container;

  setUp(() {
    mockStorage = MockFlutterSecureStorage();
    mockApiClient = MockApiClient();

    // Set up default mocks
    when(() => mockStorage.read(key: any(named: 'key')))
        .thenAnswer((_) async => null);
    when(() => mockStorage.write(key: any(named: 'key'), value: any(named: 'value')))
        .thenAnswer((_) async {});
    when(() => mockStorage.delete(key: any(named: 'key')))
        .thenAnswer((_) async {});
  });

  tearDown(() {
    container.dispose();
  });

  ProviderContainer createContainer() {
    return ProviderContainer(
      overrides: [
        secureStorageProvider.overrideWithValue(mockStorage),
        apiClientProvider.overrideWithValue(mockApiClient),
      ],
    );
  }

  group('AuthNotifier -', () {
    group('Initial State', () {
      test('starts with unauthenticated state', () async {
        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);
        expect(state.user, isNull);
        expect(state.accessToken, isNull);
        expect(state.isLoading, isFalse);
      });

      test('checks auth status on initialization', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _fakeAccessToken);

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        verify(() => mockStorage.read(key: 'access_token')).called(1);
      });

      test('restores session if valid token exists', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _fakeAccessToken);

        container = createContainer();

        // Wait for initialization to complete
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isTrue);
        expect(state.accessToken, equals(_fakeAccessToken));
        expect(state.user, isNotNull);
        expect(state.user!.id, equals('user123'));
        expect(state.user!.role, equals('doctor'));
        expect(state.user!.clinicId, equals('clinic1'));
      });

      test('does not restore session if token is expired', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _expiredAccessToken);
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => null);

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);
      });
    });

    group('Login', () {
      test('successfully logs in user', () async {
        container = createContainer();

        final authResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: _fakeRefreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.login(any(), any()))
            .thenAnswer((_) async => authResponse);

        final notifier = container.read(authStateProvider.notifier);
        await notifier.login('doctor@example.com', 'password123');

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isTrue);
        expect(state.isLoading, isFalse);
        expect(state.error, isNull);
        expect(state.accessToken, equals(_fakeAccessToken));
        expect(state.user, isNotNull);
        expect(state.user!.role, equals('doctor'));

        verify(() => mockApiClient.login('doctor@example.com', 'password123'))
            .called(1);
        verify(() => mockStorage.write(
            key: 'access_token', value: _fakeAccessToken)).called(1);
        verify(() => mockStorage.write(
            key: 'refresh_token', value: _fakeRefreshToken)).called(1);
      });

      test('sets loading state during login', () async {
        container = createContainer();

        final authResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: _fakeRefreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.login(any(), any())).thenAnswer((_) async {
          await Future.delayed(const Duration(milliseconds: 100));
          return authResponse;
        });

        final notifier = container.read(authStateProvider.notifier);
        final loginFuture = notifier.login('test@example.com', 'password');

        // Check loading state immediately
        await Future.delayed(const Duration(milliseconds: 10));
        expect(container.read(authStateProvider).isLoading, isTrue);

        await loginFuture;
        expect(container.read(authStateProvider).isLoading, isFalse);
      });

      test('handles login failure', () async {
        container = createContainer();

        when(() => mockApiClient.login(any(), any()))
            .thenThrow(Exception('Invalid credentials'));

        final notifier = container.read(authStateProvider.notifier);
        await notifier.login('wrong@example.com', 'wrongpassword');

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);
        expect(state.isLoading, isFalse);
        expect(state.error, contains('Invalid credentials'));
        expect(state.user, isNull);

        verifyNever(() => mockStorage.write(
            key: any(named: 'key'), value: any(named: 'value')));
      });

      test('extracts user info from JWT token', () async {
        container = createContainer();

        final authResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: _fakeRefreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.login(any(), any()))
            .thenAnswer((_) async => authResponse);

        final notifier = container.read(authStateProvider.notifier);
        await notifier.login('test@example.com', 'password');

        final state = container.read(authStateProvider);
        expect(state.user!.id, equals('user123'));
        expect(state.user!.role, equals('doctor'));
        expect(state.user!.clinicId, equals('clinic1'));
      });

      test('clears previous error on new login attempt', () async {
        container = createContainer();

        // First login fails
        when(() => mockApiClient.login(any(), any()))
            .thenThrow(Exception('Error'));

        final notifier = container.read(authStateProvider.notifier);
        await notifier.login('test@example.com', 'wrong');

        expect(container.read(authStateProvider).error, isNotNull);

        // Second login succeeds
        final authResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: _fakeRefreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.login(any(), any()))
            .thenAnswer((_) async => authResponse);

        await notifier.login('test@example.com', 'correct');

        expect(container.read(authStateProvider).error, isNull);
      });
    });

    group('Logout', () {
      test('successfully logs out user', () async {
        // First login
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _fakeAccessToken);

        container = createContainer();
        await Future.delayed(const Duration(milliseconds: 100));

        expect(container.read(authStateProvider).isAuthenticated, isTrue);

        // Then logout
        final notifier = container.read(authStateProvider.notifier);
        await notifier.logout();

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);
        expect(state.user, isNull);
        expect(state.accessToken, isNull);
        expect(state.error, isNull);

        verify(() => mockStorage.delete(key: 'access_token')).called(1);
        verify(() => mockStorage.delete(key: 'refresh_token')).called(1);
      });

      test('clears all user data on logout', () async {
        // Setup authenticated state
        final authResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: _fakeRefreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.login(any(), any()))
            .thenAnswer((_) async => authResponse);

        container = createContainer();
        final notifier = container.read(authStateProvider.notifier);
        await notifier.login('test@example.com', 'password');

        expect(container.read(authStateProvider).isAuthenticated, isTrue);

        // Logout
        await notifier.logout();

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);
        expect(state.isLoading, isFalse);
        expect(state.user, isNull);
        expect(state.accessToken, isNull);
        expect(state.error, isNull);
      });
    });

    group('Token Refresh', () {
      test('refreshes token when access token is expired but refresh token exists', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _expiredAccessToken);
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => _fakeRefreshToken);

        final newAuthResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: _fakeRefreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.refreshToken(any()))
            .thenAnswer((_) async => newAuthResponse);

        container = createContainer();

        // Wait for initialization and token refresh
        await Future.delayed(const Duration(milliseconds: 100));

        verify(() => mockApiClient.refreshToken(_fakeRefreshToken)).called(1);

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isTrue);
        expect(state.accessToken, equals(_fakeAccessToken));
      });

      test('logs out if token refresh fails', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _expiredAccessToken);
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => _fakeRefreshToken);
        when(() => mockApiClient.refreshToken(any()))
            .thenThrow(Exception('Refresh failed'));

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);

        verify(() => mockStorage.delete(key: 'access_token')).called(1);
        verify(() => mockStorage.delete(key: 'refresh_token')).called(1);
      });

      test('stores new tokens after successful refresh', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _expiredAccessToken);
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => _fakeRefreshToken);

        final newAuthResponse = AuthResponse(
          accessToken: _fakeAccessToken,
          refreshToken: 'new_refresh_token',
          tokenType: 'Bearer',
          expiresIn: 3600,
        );

        when(() => mockApiClient.refreshToken(any()))
            .thenAnswer((_) async => newAuthResponse);

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        verify(() => mockStorage.write(
            key: 'access_token', value: _fakeAccessToken)).called(1);
        verify(() => mockStorage.write(
            key: 'refresh_token', value: 'new_refresh_token')).called(1);
      });
    });

    group('Auto-logout on Token Expiry', () {
      test('automatically logs out when token expires and no refresh token', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _expiredAccessToken);
        when(() => mockStorage.read(key: 'refresh_token'))
            .thenAnswer((_) async => null);

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isFalse);
        expect(state.accessToken, isNull);
      });

      test('does not auto-logout if token is still valid', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenAnswer((_) async => _fakeAccessToken);

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isAuthenticated, isTrue);
        expect(state.accessToken, equals(_fakeAccessToken));
      });
    });

    group('State Management', () {
      test('copyWith preserves unchanged values', () {
        final state = const AuthState(
          isAuthenticated: true,
          isLoading: false,
          user: User(id: 'u1', role: 'doctor'),
          accessToken: 'token123',
          error: 'Some error',
        );

        final newState = state.copyWith(isLoading: true);

        expect(newState.isAuthenticated, isTrue);
        expect(newState.user!.id, equals('u1'));
        expect(newState.accessToken, equals('token123'));
        expect(newState.isLoading, isTrue);
        expect(newState.error, equals('Some error'));
      });

      test('copyWith updates only specified values', () {
        final state = const AuthState();

        final newState = state.copyWith(
          isAuthenticated: true,
          accessToken: 'new_token',
        );

        expect(newState.isAuthenticated, isTrue);
        expect(newState.accessToken, equals('new_token'));
        expect(newState.isLoading, isFalse); // Unchanged
        expect(newState.user, isNull); // Unchanged
      });
    });

    group('User Model Helpers', () {
      test('isAdmin returns true for admin role', () {
        final user = const User(id: '1', role: 'admin');
        expect(user.isAdmin, isTrue);
        expect(user.isDoctor, isFalse);
        expect(user.isReceptionist, isFalse);
      });

      test('isDoctor returns true for doctor role', () {
        final user = const User(id: '1', role: 'doctor');
        expect(user.isDoctor, isTrue);
        expect(user.isAdmin, isFalse);
        expect(user.isReceptionist, isFalse);
      });

      test('isReceptionist returns true for receptionist role', () {
        final user = const User(id: '1', role: 'receptionist');
        expect(user.isReceptionist, isTrue);
        expect(user.isAdmin, isFalse);
        expect(user.isDoctor, isFalse);
      });
    });

    group('Error Handling', () {
      test('handles network errors during login', () async {
        container = createContainer();

        when(() => mockApiClient.login(any(), any()))
            .thenThrow(Exception('Network error'));

        final notifier = container.read(authStateProvider.notifier);
        await notifier.login('test@example.com', 'password');

        final state = container.read(authStateProvider);
        expect(state.error, contains('Network error'));
        expect(state.isAuthenticated, isFalse);
      });

      test('handles storage errors during initialization', () async {
        when(() => mockStorage.read(key: 'access_token'))
            .thenThrow(Exception('Storage error'));

        container = createContainer();

        // Wait for initialization
        await Future.delayed(const Duration(milliseconds: 100));

        final state = container.read(authStateProvider);
        expect(state.isLoading, isFalse);
        expect(state.error, isNotNull);
      });
    });
  });
}
