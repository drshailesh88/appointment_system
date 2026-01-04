'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { apiClient, Doctor } from '@/lib/api-client';
import DoctorCard from '@/components/DoctorCard';

function DoctorsPageContent() {
  const searchParams = useSearchParams();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    specialization: searchParams.get('specialization') || '',
    city: searchParams.get('city') || '',
  });

  useEffect(() => {
    fetchDoctors();
  }, [filters]);

  const fetchDoctors = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.listDoctors({
        specialization: filters.specialization || undefined,
        city: filters.city || undefined,
      });
      setDoctors(result);
    } catch (err: any) {
      setError(err.message || 'Failed to load doctors');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

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
            <nav className="flex gap-4">
              <Link
                href="/doctors"
                className="text-blue-600 font-semibold"
              >
                Find Doctors
              </Link>
              <Link
                href="/appointments"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                My Appointments
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Filter Doctors
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="specialization" className="block text-sm font-medium text-gray-700 mb-2">
                Specialization
              </label>
              <input
                type="text"
                id="specialization"
                value={filters.specialization}
                onChange={(e) => handleFilterChange('specialization', e.target.value)}
                placeholder="e.g. Cardiology, Dentistry"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-2">
                City
              </label>
              <input
                type="text"
                id="city"
                value={filters.city}
                onChange={(e) => handleFilterChange('city', e.target.value)}
                placeholder="e.g. Mumbai, Delhi"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Results Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            {loading ? 'Loading...' : `${doctors.length} Doctors Available`}
          </h2>
          {filters.specialization && (
            <p className="text-gray-600 mt-1">
              Showing results for &quot;{filters.specialization}&quot;
            </p>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600"></div>
            <p className="text-gray-600 mt-4">Loading doctors...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg">
            {error}
          </div>
        )}

        {/* No Results */}
        {!loading && !error && doctors.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No Doctors Found
            </h3>
            <p className="text-gray-600 mb-6">
              Try adjusting your search filters
            </p>
            <Link
              href="/doctors"
              onClick={() => setFilters({ specialization: '', city: '' })}
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Clear Filters
            </Link>
          </div>
        )}

        {/* Doctors List */}
        {!loading && !error && doctors.length > 0 && (
          <div className="space-y-4">
            {doctors.map((doctor) => (
              <DoctorCard key={doctor.id} doctor={doctor} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default function DoctorsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <DoctorsPageContent />
    </Suspense>
  );
}
