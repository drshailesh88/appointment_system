'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient, Doctor, Slot, BookingRequest } from '@/lib/api-client';
import SlotPicker from '@/components/SlotPicker';
import OTPVerification from '@/components/OTPVerification';

export default function DoctorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const doctorId = params.id as string;

  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [showBooking, setShowBooking] = useState(false);
  const [showOTP, setShowOTP] = useState(false);
  const [bookingData, setBookingData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    chief_complaint: '',
  });
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);

  useEffect(() => {
    if (doctorId) {
      fetchDoctor();
    }
  }, [doctorId]);

  const fetchDoctor = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.getDoctor(doctorId);
      setDoctor(result);
    } catch (err: any) {
      setError(err.message || 'Failed to load doctor details');
    } finally {
      setLoading(false);
    }
  };

  const handleSlotSelect = (slot: Slot) => {
    setSelectedSlot(slot);
    setShowBooking(true);
  };

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check if user is authenticated
    if (!apiClient.isAuthenticated()) {
      setShowOTP(true);
      return;
    }

    await submitBooking();
  };

  const submitBooking = async () => {
    if (!selectedSlot || !doctor) return;

    setBookingLoading(true);
    setBookingError(null);

    try {
      const booking: BookingRequest = {
        doctor_id: doctorId,
        scheduled_start: selectedSlot.start_time,
        duration_minutes: doctor.slot_duration || 15,
        first_name: bookingData.first_name,
        last_name: bookingData.last_name,
        phone: bookingData.phone,
        email: bookingData.email,
        chief_complaint: bookingData.chief_complaint,
      };

      const appointment = await apiClient.bookAppointment(booking);

      // Redirect to appointments page
      router.push(`/appointments/${appointment.id}`);
    } catch (err: any) {
      setBookingError(err.message || 'Failed to book appointment');
    } finally {
      setBookingLoading(false);
    }
  };

  const handleOTPSuccess = () => {
    setShowOTP(false);
    submitBooking();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600"></div>
          <p className="text-gray-600 mt-4">Loading doctor details...</p>
        </div>
      </div>
    );
  }

  if (error || !doctor) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">😞</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            Doctor Not Found
          </h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link
            href="/doctors"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Back to Doctors
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/doctors" className="flex items-center gap-2 text-blue-600 hover:text-blue-700">
            <span>←</span>
            <span className="font-medium">Back to Doctors</span>
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Doctor Info */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6 sticky top-8">
              {doctor.photo_url ? (
                <img
                  src={doctor.photo_url}
                  alt={doctor.name}
                  className="w-32 h-32 rounded-full object-cover mx-auto mb-4"
                />
              ) : (
                <div className="w-32 h-32 rounded-full bg-blue-100 flex items-center justify-center mx-auto mb-4">
                  <span className="text-4xl font-semibold text-blue-600">
                    {doctor.name.charAt(0)}
                  </span>
                </div>
              )}

              <h1 className="text-2xl font-bold text-gray-900 text-center mb-2">
                {doctor.name}
              </h1>

              {doctor.specialization && (
                <p className="text-blue-600 font-medium text-center mb-4">
                  {doctor.specialization}
                </p>
              )}

              {doctor.qualification && (
                <p className="text-gray-600 text-center text-sm mb-4">
                  {doctor.qualification}
                </p>
              )}

              <div className="border-t border-gray-200 pt-4 space-y-3">
                {doctor.experience_years && (
                  <div className="flex items-center text-sm text-gray-700">
                    <span className="mr-2">📅</span>
                    <span>{doctor.experience_years} years experience</span>
                  </div>
                )}
                {doctor.languages && doctor.languages.length > 0 && (
                  <div className="flex items-center text-sm text-gray-700">
                    <span className="mr-2">💬</span>
                    <span>{doctor.languages.join(', ')}</span>
                  </div>
                )}
                {doctor.clinic_name && (
                  <div className="flex items-start text-sm text-gray-700">
                    <span className="mr-2">🏥</span>
                    <div>
                      <div className="font-medium">{doctor.clinic_name}</div>
                      {doctor.clinic_address && (
                        <div className="text-gray-500 mt-1">{doctor.clinic_address}</div>
                      )}
                    </div>
                  </div>
                )}
                {doctor.registration_number && (
                  <div className="flex items-center text-sm text-gray-700">
                    <span className="mr-2">🆔</span>
                    <span>Reg: {doctor.registration_number}</span>
                  </div>
                )}
              </div>

              <div className="border-t border-gray-200 mt-4 pt-4">
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600">
                    ₹{doctor.consultation_fee}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Consultation Fee
                  </div>
                </div>
              </div>

              {doctor.bio && (
                <div className="border-t border-gray-200 mt-4 pt-4">
                  <h3 className="font-semibold text-gray-900 mb-2">About</h3>
                  <p className="text-sm text-gray-600">{doctor.bio}</p>
                </div>
              )}
            </div>
          </div>

          {/* Booking Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* Slot Picker */}
            <SlotPicker
              doctorId={doctorId}
              onSelectSlot={handleSlotSelect}
              selectedSlot={selectedSlot}
            />

            {/* Booking Form */}
            {showBooking && selectedSlot && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  Patient Details
                </h3>

                {bookingError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                    {bookingError}
                  </div>
                )}

                <form onSubmit={handleBookingSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="first_name" className="block text-sm font-medium text-gray-700 mb-2">
                        First Name *
                      </label>
                      <input
                        type="text"
                        id="first_name"
                        required
                        value={bookingData.first_name}
                        onChange={(e) => setBookingData(prev => ({ ...prev, first_name: e.target.value }))}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label htmlFor="last_name" className="block text-sm font-medium text-gray-700 mb-2">
                        Last Name
                      </label>
                      <input
                        type="text"
                        id="last_name"
                        value={bookingData.last_name}
                        onChange={(e) => setBookingData(prev => ({ ...prev, last_name: e.target.value }))}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                        Phone Number *
                      </label>
                      <input
                        type="tel"
                        id="phone"
                        required
                        pattern="[0-9]{10,15}"
                        value={bookingData.phone}
                        onChange={(e) => setBookingData(prev => ({ ...prev, phone: e.target.value }))}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                        Email
                      </label>
                      <input
                        type="email"
                        id="email"
                        value={bookingData.email}
                        onChange={(e) => setBookingData(prev => ({ ...prev, email: e.target.value }))}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="chief_complaint" className="block text-sm font-medium text-gray-700 mb-2">
                      Reason for Visit
                    </label>
                    <textarea
                      id="chief_complaint"
                      rows={3}
                      value={bookingData.chief_complaint}
                      onChange={(e) => setBookingData(prev => ({ ...prev, chief_complaint: e.target.value }))}
                      placeholder="Brief description of your symptoms or reason for consultation"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-900 mb-2">Booking Summary</h4>
                    <div className="space-y-1 text-sm text-gray-700">
                      <p>Doctor: <strong>{doctor.name}</strong></p>
                      <p>Date & Time: <strong>{new Date(selectedSlot.start_time).toLocaleString('en-IN')}</strong></p>
                      <p>Duration: <strong>{doctor.slot_duration} minutes</strong></p>
                      <p>Fee: <strong>₹{doctor.consultation_fee}</strong></p>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={bookingLoading}
                    className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-semibold text-lg"
                  >
                    {bookingLoading ? 'Booking...' : 'Confirm Booking'}
                  </button>
                </form>
              </div>
            )}

            {/* OTP Modal */}
            {showOTP && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                <div className="max-w-md w-full">
                  <OTPVerification
                    onSuccess={handleOTPSuccess}
                    onCancel={() => setShowOTP(false)}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
