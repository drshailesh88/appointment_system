'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient, Appointment } from '@/lib/api-client';

export default function AppointmentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = params.id as string;

  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiClient.isAuthenticated()) {
      router.push('/appointments');
      return;
    }

    if (appointmentId) {
      fetchAppointment();
    }
  }, [appointmentId]);

  const fetchAppointment = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.getAppointment(appointmentId);
      setAppointment(result);
    } catch (err: any) {
      setError(err.message || 'Failed to load appointment details');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this appointment?')) {
      return;
    }

    try {
      await apiClient.cancelAppointment(appointmentId, 'Cancelled by patient');
      router.push('/appointments');
    } catch (err: any) {
      alert(err.message || 'Failed to cancel appointment');
    }
  };

  const formatDateTime = (datetime: string) => {
    const date = new Date(datetime);
    return {
      date: date.toLocaleDateString('en-IN', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }),
      time: date.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      }),
    };
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'checked_in':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'completed':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'cancelled':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'no_show':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600"></div>
          <p className="text-gray-600 mt-4">Loading appointment...</p>
        </div>
      </div>
    );
  }

  if (error || !appointment) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">😞</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            Appointment Not Found
          </h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link
            href="/appointments"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Back to Appointments
          </Link>
        </div>
      </div>
    );
  }

  const { date, time } = formatDateTime(appointment.scheduled_start);
  const canCancel = appointment.status.toLowerCase() === 'scheduled';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/appointments" className="flex items-center gap-2 text-blue-600 hover:text-blue-700">
            <span>←</span>
            <span className="font-medium">Back to Appointments</span>
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {/* Status Banner */}
          <div className={`px-6 py-4 border-b-2 ${getStatusColor(appointment.status)}`}>
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">
                Appointment {appointment.status.replace(/_/g, ' ')}
              </h2>
              {appointment.token_number && (
                <div className="text-right">
                  <div className="text-2xl font-bold">#{appointment.token_number}</div>
                  <div className="text-xs">Token Number</div>
                </div>
              )}
            </div>
          </div>

          {/* Appointment Details */}
          <div className="p-6 space-y-6">
            {/* Doctor Info */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Doctor</h3>
              <p className="text-xl font-semibold text-gray-900">
                {appointment.doctor_name}
              </p>
            </div>

            {/* Date & Time */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Date</h3>
                <div className="flex items-center text-gray-900">
                  <span className="mr-2">📅</span>
                  <span>{date}</span>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Time</h3>
                <div className="flex items-center text-gray-900">
                  <span className="mr-2">🕐</span>
                  <span>{time} ({appointment.duration_minutes} mins)</span>
                </div>
              </div>
            </div>

            {/* Patient Info */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Patient Name</h3>
              <p className="text-gray-900">{appointment.patient_name}</p>
            </div>

            {/* Appointment Type */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Appointment Type</h3>
              <p className="text-gray-900">{appointment.appointment_type.replace(/_/g, ' ')}</p>
            </div>

            {/* Chief Complaint */}
            {appointment.chief_complaint && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Reason for Visit</h3>
                <p className="text-gray-900">{appointment.chief_complaint}</p>
              </div>
            )}

            {/* Appointment ID */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Appointment ID</h3>
              <p className="text-gray-600 text-sm font-mono">{appointment.id}</p>
            </div>
          </div>

          {/* Actions */}
          {canCancel && (
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <button
                onClick={handleCancel}
                className="w-full bg-red-600 text-white py-3 px-6 rounded-lg hover:bg-red-700 transition-colors font-semibold"
              >
                Cancel Appointment
              </button>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-semibold text-gray-900 mb-3">
            Important Instructions
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start">
              <span className="mr-2">✓</span>
              <span>Please arrive 10 minutes before your appointment time</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">✓</span>
              <span>Bring your previous medical records if any</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">✓</span>
              <span>Wear a mask and maintain social distancing</span>
            </li>
            {appointment.token_number && (
              <li className="flex items-start">
                <span className="mr-2">✓</span>
                <span>Your token number is <strong>#{appointment.token_number}</strong></span>
              </li>
            )}
          </ul>
        </div>
      </main>
    </div>
  );
}
