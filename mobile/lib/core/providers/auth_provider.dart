import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

import '../api/api_client.dart';
import '../models/user.dart';

/// Auth state
class AuthState {
  final bool isAuthenticated;
  final bool isLoading;
  final User? user;
  final String? accessToken;
  final String? error;

  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = false,
    this.user,
    this.accessToken,
    this.error,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    User? user,
    String? accessToken,
    String? error,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      user: user ?? this.user,
      accessToken: accessToken ?? this.accessToken,
      error: error ?? this.error,
    );
  }
}

/// Auth state notifier
class AuthNotifier extends StateNotifier<AuthState> {
  final FlutterSecureStorage _storage;
  final ApiClient _apiClient;

  AuthNotifier(this._storage, this._apiClient) : super(const AuthState()) {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    state = state.copyWith(isLoading: true);

    try {
      final accessToken = await _storage.read(key: 'access_token');
      final refreshToken = await _storage.read(key: 'refresh_token');

      if (accessToken != null && !JwtDecoder.isExpired(accessToken)) {
        final payload = JwtDecoder.decode(accessToken);
        state = state.copyWith(
          isAuthenticated: true,
          isLoading: false,
          accessToken: accessToken,
          user: User(
            id: payload['sub'],
            role: payload['role'],
            clinicId: payload['clinic_id'],
          ),
        );
      } else if (refreshToken != null) {
        await _refreshToken(refreshToken);
      } else {
        state = state.copyWith(isLoading: false);
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _apiClient.login(email, password);

      await _storage.write(key: 'access_token', value: response.accessToken);
      await _storage.write(key: 'refresh_token', value: response.refreshToken);

      final payload = JwtDecoder.decode(response.accessToken);

      state = state.copyWith(
        isAuthenticated: true,
        isLoading: false,
        accessToken: response.accessToken,
        user: User(
          id: payload['sub'],
          role: payload['role'],
          clinicId: payload['clinic_id'],
        ),
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Login failed: ${e.toString()}',
      );
    }
  }

  Future<void> _refreshToken(String refreshToken) async {
    try {
      final response = await _apiClient.refreshToken(refreshToken);

      await _storage.write(key: 'access_token', value: response.accessToken);
      await _storage.write(key: 'refresh_token', value: response.refreshToken);

      final payload = JwtDecoder.decode(response.accessToken);

      state = state.copyWith(
        isAuthenticated: true,
        isLoading: false,
        accessToken: response.accessToken,
        user: User(
          id: payload['sub'],
          role: payload['role'],
          clinicId: payload['clinic_id'],
        ),
      );
    } catch (e) {
      await logout();
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');

    state = const AuthState();
  }
}

/// Secure storage provider
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});

/// API client provider
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

/// Auth state provider
final authStateProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final storage = ref.watch(secureStorageProvider);
  final apiClient = ref.watch(apiClientProvider);
  return AuthNotifier(storage, apiClient);
});
