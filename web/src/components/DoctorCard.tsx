'use client';

import Link from 'next/link';
import { Doctor } from '@/lib/api-client';

interface DoctorCardProps {
  doctor: Doctor;
}

export default function DoctorCard({ doctor }: DoctorCardProps) {
  return (
    <Link href={`/doctors/${doctor.id}`}>
      <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 cursor-pointer border border-gray-200">
        <div className="flex items-start gap-4">
          {/* Doctor Photo */}
          <div className="flex-shrink-0">
            {doctor.photo_url ? (
              <img
                src={doctor.photo_url}
                alt={doctor.name}
                className="w-20 h-20 rounded-full object-cover"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="text-2xl font-semibold text-blue-600">
                  {doctor.name.charAt(0)}
                </span>
              </div>
            )}
          </div>

          {/* Doctor Info */}
          <div className="flex-1 min-w-0">
            <h3 className="text-xl font-semibold text-gray-900 truncate">
              {doctor.name}
            </h3>

            {doctor.specialization && (
              <p className="text-sm text-blue-600 font-medium mt-1">
                {doctor.specialization}
              </p>
            )}

            {doctor.qualification && (
              <p className="text-sm text-gray-600 mt-1">
                {doctor.qualification}
              </p>
            )}

            <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-600">
              {doctor.experience_years && (
                <span>
                  📅 {doctor.experience_years} years exp.
                </span>
              )}
              {doctor.languages && doctor.languages.length > 0 && (
                <span>
                  💬 {doctor.languages.join(', ')}
                </span>
              )}
            </div>

            {doctor.clinic_name && (
              <p className="text-sm text-gray-500 mt-2">
                🏥 {doctor.clinic_name}
              </p>
            )}
          </div>

          {/* Consultation Fee */}
          <div className="flex-shrink-0 text-right">
            <div className="text-2xl font-bold text-green-600">
              ₹{doctor.consultation_fee}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Consultation
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
