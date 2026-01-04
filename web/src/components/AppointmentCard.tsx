'use client';

import Link from 'next/link';
import { Appointment } from '@/lib/api-client';

interface AppointmentCardProps {
  appointment: Appointment;
  onCancel?: (id: string) => void;
}

export default function AppointmentCard({ appointment, onCancel }: AppointmentCardProps) {
  const formatDateTime = (datetime: string) => {
    const date = new Date(datetime);
    return {
      date: date.toLocaleDateString('en-IN', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      }),
      time: date.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      }),
    };
  };

  const { date, time } = formatDateTime(appointment.scheduled_start);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'checked_in':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-gray-100 text-gray-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      case 'no_show':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const canCancel = appointment.status.toLowerCase() === 'scheduled';

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {appointment.doctor_name}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {appointment.appointment_type.replace(/_/g, ' ')}
            </p>
          </div>

          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(appointment.status)}`}>
            {appointment.status.replace(/_/g, ' ')}
          </span>
        </div>

        <div className="space-y-2 mb-4">
          <div className="flex items-center text-sm text-gray-700">
            <span className="mr-2">📅</span>
            <span>{date}</span>
          </div>
          <div className="flex items-center text-sm text-gray-700">
            <span className="mr-2">🕐</span>
            <span>{time} ({appointment.duration_minutes} mins)</span>
          </div>
          {appointment.token_number && (
            <div className="flex items-center text-sm text-gray-700">
              <span className="mr-2">🎫</span>
              <span>Token #{appointment.token_number}</span>
            </div>
          )}
          {appointment.chief_complaint && (
            <div className="flex items-start text-sm text-gray-700">
              <span className="mr-2">📝</span>
              <span>{appointment.chief_complaint}</span>
            </div>
          )}
        </div>

        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <Link
            href={`/appointments/${appointment.id}`}
            className="flex-1 text-center px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors font-medium"
          >
            View Details
          </Link>

          {canCancel && onCancel && (
            <button
              onClick={() => onCancel(appointment.id)}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
