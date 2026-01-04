import 'package:dio/dio.dart';

import '../../config/app_config.dart';
import '../models/auth_response.dart';

/// API client for backend communication
class ApiClient {
  late final Dio _dio;

  ApiClient() {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.baseUrl,
        connectTimeout: AppConfig.connectionTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Add interceptors
    _dio.interceptors.add(
      InterceptorsWrapper(
        onError: (error, handler) {
          // Handle errors globally
          handler.next(error);
        },
      ),
    );
  }

  /// Set auth token for subsequent requests
  void setAuthToken(String token) {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  /// Clear auth token
  void clearAuthToken() {
    _dio.options.headers.remove('Authorization');
  }

  /// Login with email/phone and password
  Future<AuthResponse> login(String emailOrPhone, String password) async {
    final response = await _dio.post(
      '/auth/login',
      data: {
        'username': emailOrPhone,
        'password': password,
      },
      options: Options(
        contentType: Headers.formUrlEncodedContentType,
      ),
    );

    return AuthResponse.fromJson(response.data);
  }

  /// Refresh access token
  Future<AuthResponse> refreshToken(String refreshToken) async {
    final response = await _dio.post(
      '/auth/refresh',
      queryParameters: {'refresh_token': refreshToken},
    );

    return AuthResponse.fromJson(response.data);
  }

  /// Get current user
  Future<Map<String, dynamic>> getCurrentUser() async {
    final response = await _dio.get('/auth/me');
    return response.data;
  }

  // Appointments

  /// Get today's appointments
  Future<List<Map<String, dynamic>>> getTodayAppointments({
    String? doctorId,
  }) async {
    final response = await _dio.get(
      '/appointments/today',
      queryParameters: doctorId != null ? {'doctor_id': doctorId} : null,
    );
    return List<Map<String, dynamic>>.from(response.data);
  }

  /// Get appointments with filters
  Future<List<Map<String, dynamic>>> getAppointments({
    String? doctorId,
    String? patientId,
    String? dateFrom,
    String? dateTo,
    String? status,
    int skip = 0,
    int limit = 100,
  }) async {
    final response = await _dio.get(
      '/appointments',
      queryParameters: {
        if (doctorId != null) 'doctor_id': doctorId,
        if (patientId != null) 'patient_id': patientId,
        if (dateFrom != null) 'date_from': dateFrom,
        if (dateTo != null) 'date_to': dateTo,
        if (status != null) 'status_filter': status,
        'skip': skip,
        'limit': limit,
      },
    );
    return List<Map<String, dynamic>>.from(response.data);
  }

  /// Create appointment
  Future<Map<String, dynamic>> createAppointment(
    Map<String, dynamic> data,
  ) async {
    final response = await _dio.post('/appointments', data: data);
    return response.data;
  }

  /// Get available slots
  Future<Map<String, dynamic>> getAvailableSlots({
    required String doctorId,
    required String date,
    int durationMinutes = 15,
  }) async {
    final response = await _dio.post(
      '/appointments/slots/availability',
      data: {
        'doctor_id': doctorId,
        'date': date,
        'duration_minutes': durationMinutes,
      },
    );
    return response.data;
  }

  /// Check in patient
  Future<Map<String, dynamic>> checkInPatient(
    String appointmentId, {
    int? tokenNumber,
  }) async {
    final response = await _dio.post(
      '/appointments/$appointmentId/check-in',
      data: tokenNumber != null ? {'token_number': tokenNumber} : null,
    );
    return response.data;
  }

  // Patients

  /// Search patients
  Future<List<Map<String, dynamic>>> searchPatients({
    required String query,
    String? clinicId,
    int limit = 20,
  }) async {
    final response = await _dio.get(
      '/patients/search',
      queryParameters: {
        'q': query,
        if (clinicId != null) 'clinic_id': clinicId,
        'limit': limit,
      },
    );
    return List<Map<String, dynamic>>.from(response.data);
  }

  /// Get patient by ID
  Future<Map<String, dynamic>> getPatient(String patientId) async {
    final response = await _dio.get('/patients/$patientId');
    return response.data;
  }

  /// Create patient
  Future<Map<String, dynamic>> createPatient(
    Map<String, dynamic> data,
  ) async {
    final response = await _dio.post('/patients', data: data);
    return response.data;
  }

  // Doctors

  /// Get doctors
  Future<List<Map<String, dynamic>>> getDoctors({
    String? clinicId,
    String? specialization,
    bool activeOnly = true,
  }) async {
    final response = await _dio.get(
      '/doctors',
      queryParameters: {
        if (clinicId != null) 'clinic_id': clinicId,
        if (specialization != null) 'specialization': specialization,
        'active_only': activeOnly,
      },
    );
    return List<Map<String, dynamic>>.from(response.data);
  }

  /// Get doctor by ID
  Future<Map<String, dynamic>> getDoctor(String doctorId) async {
    final response = await _dio.get('/doctors/$doctorId');
    return response.data;
  }

  /// Get doctor schedule
  Future<Map<String, dynamic>> getDoctorSchedule(
    String doctorId, {
    String? date,
  }) async {
    final response = await _dio.get(
      '/appointments/doctor/$doctorId/schedule',
      queryParameters: date != null ? {'schedule_date': date} : null,
    );
    return response.data;
  }

  // Clinic

  /// Get clinic stats
  Future<Map<String, dynamic>> getClinicStats(String clinicId) async {
    final response = await _dio.get('/clinics/$clinicId/stats');
    return response.data;
  }

  // Generic HTTP methods for flexible API calls

  /// Generic GET request
  Future<dynamic> get(String path, {Map<String, dynamic>? queryParameters}) async {
    final response = await _dio.get(path, queryParameters: queryParameters);
    return response.data;
  }

  /// Generic POST request
  Future<dynamic> post(String path, dynamic data) async {
    final response = await _dio.post(path, data: data);
    return response.data;
  }

  /// Generic PUT request
  Future<dynamic> put(String path, dynamic data) async {
    final response = await _dio.put(path, data: data);
    return response.data;
  }

  /// Generic DELETE request
  Future<dynamic> delete(String path) async {
    final response = await _dio.delete(path);
    return response.data;
  }

  /// Generic PATCH request
  Future<dynamic> patch(String path, dynamic data) async {
    final response = await _dio.patch(path, data: data);
    return response.data;
  }
}
