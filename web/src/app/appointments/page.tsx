'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient, Appointment } from '@/lib/api-client';
import AppointmentCard from '@/components/AppointmentCard';
import OTPVerification from '@/components/OTPVerification';

export default function AppointmentsPage() {
  const router = useRouter();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showOTP, setShowOTP] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('');

  useEffect(() => {
    if (apiClient.isAuthenticated()) {
      fetchAppointments();
    } else {
      setShowOTP(true);
      setLoading(false);
    }
  }, [filterStatus]);

  const fetchAppointments = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.getMyAppointments({
        status_filter: filterStatus || undefined,
      });
      setAppointments(result);
    } catch (err: any) {
      setError(err.message || 'Failed to load appointments');
    } finally {
      setLoading(false);
    }
  };

  const handleOTPSuccess = () => {
    setShowOTP(false);
    fetchAppointments();
  };

  const handleCancelAppointment = async (appointmentId: string) => {
    if (!confirm('Are you sure you want to cancel this appointment?')) {
      return;
    }

    try {
      await apiClient.cancelAppointment(appointmentId, 'Cancelled by patient');
      // Refresh appointments list
      fetchAppointments();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel appointment');
    }
  };

  const handleLogout = () => {
    apiClient.logout();
    setShowOTP(true);
    setAppointments([]);
  };

  if (showOTP && !apiClient.isAuthenticated()) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              My Appointments
            </h1>
            <p className="text-gray-600">
              Login with OTP to view your appointments
            </p>
          </div>
          <OTPVerification
            onSuccess={handleOTPSuccess}
            onCancel={() => router.push('/')}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-xl font-bold">D</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">
                DocAssist
              </h1>
            </Link>
            <nav className="flex gap-4 items-center">
              <Link
                href="/doctors"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                Find Doctors
              </Link>
              <Link
                href="/appointments"
                className="text-blue-600 font-semibold"
              >
                My Appointments
              </Link>
              <button
                onClick={handleLogout}
                className="text-red-600 hover:text-red-700 font-medium"
              >
                Logout
              </button>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            My Appointments
          </h2>
          <p className="text-gray-600">
            View and manage your upcoming and past appointments
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilterStatus('')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterStatus === ''
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterStatus('scheduled')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterStatus === 'scheduled'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Scheduled
            </button>
            <button
              onClick={() => setFilterStatus('completed')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterStatus === 'completed'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Completed
            </button>
            <button
              onClick={() => setFilterStatus('cancelled')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterStatus === 'cancelled'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Cancelled
            </button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600"></div>
            <p className="text-gray-600 mt-4">Loading appointments...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg">
            {error}
          </div>
        )}

        {/* No Appointments */}
        {!loading && !error && appointments.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📅</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No Appointments Found
            </h3>
            <p className="text-gray-600 mb-6">
              {filterStatus
                ? `You don't have any ${filterStatus} appointments`
                : "You haven't booked any appointments yet"}
            </p>
            <Link
              href="/doctors"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Book an Appointment
            </Link>
          </div>
        )}

        {/* Appointments List */}
        {!loading && !error && appointments.length > 0 && (
          <div className="space-y-4">
            {appointments.map((appointment) => (
              <AppointmentCard
                key={appointment.id}
                appointment={appointment}
                onCancel={handleCancelAppointment}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
