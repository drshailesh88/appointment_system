'use client';

import { useState, useEffect } from 'react';
import { apiClient, Slot } from '@/lib/api-client';

interface SlotPickerProps {
  doctorId: string;
  onSelectSlot: (slot: Slot) => void;
  selectedSlot?: Slot | null;
}

export default function SlotPicker({ doctorId, onSelectSlot, selectedSlot }: SlotPickerProps) {
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generate next 7 days
  const generateDates = () => {
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date();
      date.setDate(date.getDate() + i);
      dates.push(date);
    }
    return dates;
  };

  const dates = generateDates();

  // Set default date to today
  useEffect(() => {
    if (!selectedDate) {
      setSelectedDate(dates[0].toISOString().split('T')[0]);
    }
  }, []);

  // Fetch slots when date changes
  useEffect(() => {
    if (selectedDate && doctorId) {
      fetchSlots();
    }
  }, [selectedDate, doctorId]);

  const fetchSlots = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getDoctorSlots(doctorId, selectedDate);
      setSlots(response.slots);
    } catch (err: any) {
      setError(err.message || 'Failed to load slots');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (date: Date) => {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

    return date.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short'
    });
  };

  const formatTime = (datetime: string) => {
    return new Date(datetime).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  const availableSlots = slots.filter(slot => slot.is_available);
  const morningSlots = availableSlots.filter(slot => {
    const hour = new Date(slot.start_time).getHours();
    return hour < 12;
  });
  const afternoonSlots = availableSlots.filter(slot => {
    const hour = new Date(slot.start_time).getHours();
    return hour >= 12 && hour < 17;
  });
  const eveningSlots = availableSlots.filter(slot => {
    const hour = new Date(slot.start_time).getHours();
    return hour >= 17;
  });

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4">
        Select Date & Time
      </h3>

      {/* Date Selector */}
      <div className="flex gap-2 overflow-x-auto pb-4 mb-6">
        {dates.map((date) => {
          const dateStr = date.toISOString().split('T')[0];
          const isSelected = selectedDate === dateStr;

          return (
            <button
              key={dateStr}
              onClick={() => setSelectedDate(dateStr)}
              className={`flex-shrink-0 px-4 py-3 rounded-lg border-2 transition-colors min-w-[100px] text-center ${
                isSelected
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-blue-300 text-gray-700'
              }`}
            >
              <div className="font-semibold">{formatDate(date)}</div>
              <div className="text-sm">
                {date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
              </div>
            </button>
          );
        })}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-200 border-t-blue-600"></div>
          <p className="text-gray-600 mt-2">Loading slots...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* No Slots Available */}
      {!loading && !error && slots.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No slots available for this date
        </div>
      )}

      {/* Slots by Time of Day */}
      {!loading && !error && availableSlots.length > 0 && (
        <div className="space-y-6">
          {morningSlots.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                🌅 Morning ({morningSlots.length} slots)
              </h4>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {morningSlots.map((slot, index) => (
                  <button
                    key={index}
                    onClick={() => onSelectSlot(slot)}
                    className={`px-3 py-2 rounded border text-sm font-medium transition-colors ${
                      selectedSlot?.start_time === slot.start_time
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:bg-blue-50'
                    }`}
                  >
                    {formatTime(slot.start_time)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {afternoonSlots.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                ☀️ Afternoon ({afternoonSlots.length} slots)
              </h4>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {afternoonSlots.map((slot, index) => (
                  <button
                    key={index}
                    onClick={() => onSelectSlot(slot)}
                    className={`px-3 py-2 rounded border text-sm font-medium transition-colors ${
                      selectedSlot?.start_time === slot.start_time
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:bg-blue-50'
                    }`}
                  >
                    {formatTime(slot.start_time)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {eveningSlots.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                🌙 Evening ({eveningSlots.length} slots)
              </h4>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {eveningSlots.map((slot, index) => (
                  <button
                    key={index}
                    onClick={() => onSelectSlot(slot)}
                    className={`px-3 py-2 rounded border text-sm font-medium transition-colors ${
                      selectedSlot?.start_time === slot.start_time
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:bg-blue-50'
                    }`}
                  >
                    {formatTime(slot.start_time)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && !error && availableSlots.length === 0 && slots.length > 0 && (
        <div className="text-center py-8 text-gray-500">
          All slots are booked for this date. Please select another date.
        </div>
      )}
    </div>
  );
}
