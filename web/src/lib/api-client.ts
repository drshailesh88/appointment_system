/**
 * API Client for DocAssist Practice Manager Public API
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Doctor {
  id: string;
  name: string;
  specialization: string | null;
  qualification: string | null;
  experience_years: number | null;
  consultation_fee: number;
  photo_url: string | null;
  languages: string[] | null;
  clinic_name: string | null;
  clinic_address: string | null;
  bio?: string | null;
  registration_number?: string | null;
  slot_duration?: number;
  working_hours?: Record<string, any> | null;
}

export interface Slot {
  start_time: string;
  end_time: string;
  is_available: boolean;
}

export interface SlotsResponse {
  doctor_id: string;
  date: string;
  slots: Slot[];
}

export interface BookingRequest {
  doctor_id: string;
  scheduled_start: string;
  duration_minutes: number;
  first_name: string;
  last_name?: string;
  phone: string;
  email?: string;
  date_of_birth?: string;
  gender?: 'M' | 'F' | 'O';
  chief_complaint?: string;
  notes?: string;
}

export interface Appointment {
  id: string;
  doctor_id: string;
  doctor_name: string;
  scheduled_start: string;
  duration_minutes: number;
  status: string;
  appointment_type: string;
  token_number: number | null;
  chief_complaint: string | null;
  patient_name: string;
}

export interface OTPSendResponse {
  message: string;
  expires_in_seconds: number;
}

export interface OTPVerifyResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
}

class APIClient {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = API_BASE_URL;

    // Load token from localStorage if available
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('auth_token', token);
      } else {
        localStorage.removeItem('auth_token');
      }
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token && !endpoint.includes('/otp/')) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: 'An error occurred',
      }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // OTP Endpoints
  async sendOTP(phone: string): Promise<OTPSendResponse> {
    return this.request('/public/otp/send', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
  }

  async verifyOTP(phone: string, otp_code: string): Promise<OTPVerifyResponse> {
    const response = await this.request<OTPVerifyResponse>('/public/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ phone, otp_code }),
    });

    // Store the token
    this.setToken(response.access_token);

    return response;
  }

  // Doctor Endpoints
  async listDoctors(params?: {
    specialization?: string;
    city?: string;
    skip?: number;
    limit?: number;
  }): Promise<Doctor[]> {
    const searchParams = new URLSearchParams();
    if (params?.specialization) searchParams.set('specialization', params.specialization);
    if (params?.city) searchParams.set('city', params.city);
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const endpoint = `/public/doctors${query ? `?${query}` : ''}`;

    return this.request(endpoint);
  }

  async getDoctor(doctorId: string): Promise<Doctor> {
    return this.request(`/public/doctors/${doctorId}`);
  }

  async getDoctorSlots(doctorId: string, date: string): Promise<SlotsResponse> {
    return this.request(`/public/doctors/${doctorId}/slots?date_param=${date}`);
  }

  // Appointment Endpoints (require OTP token)
  async bookAppointment(booking: BookingRequest): Promise<Appointment> {
    return this.request('/public/appointments', {
      method: 'POST',
      body: JSON.stringify(booking),
    });
  }

  async getMyAppointments(params?: {
    status_filter?: string;
    skip?: number;
    limit?: number;
  }): Promise<Appointment[]> {
    const searchParams = new URLSearchParams();
    if (params?.status_filter) searchParams.set('status_filter', params.status_filter);
    if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const endpoint = `/public/appointments${query ? `?${query}` : ''}`;

    return this.request(endpoint);
  }

  async getAppointment(appointmentId: string): Promise<Appointment> {
    return this.request(`/public/appointments/${appointmentId}`);
  }

  async cancelAppointment(appointmentId: string, reason?: string): Promise<{ message: string }> {
    return this.request(`/public/appointments/${appointmentId}`, {
      method: 'DELETE',
      body: JSON.stringify({ reason }),
    });
  }

  logout() {
    this.setToken(null);
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }
}

export const apiClient = new APIClient();
