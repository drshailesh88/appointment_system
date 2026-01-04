'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [city, setCity] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (searchQuery) params.set('specialization', searchQuery);
    if (city) params.set('city', city);

    router.push(`/doctors?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-xl font-bold">D</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">
                DocAssist
              </h1>
            </div>
            <nav className="flex gap-4">
              <Link
                href="/doctors"
                className="text-gray-600 hover:text-gray-900 font-medium"
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

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4">
            Find & Book Doctor Appointments
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Book appointments with top doctors in your area. Simple, fast, and convenient.
          </p>
        </div>

        {/* Search Box */}
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSearch} className="bg-white rounded-lg shadow-lg p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-2">
                  Specialization or Symptom
                </label>
                <input
                  type="text"
                  id="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g. Cardiologist, Dentist, Fever"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-2">
                  City
                </label>
                <input
                  type="text"
                  id="city"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="e.g. Mumbai, Delhi, Bangalore"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors font-semibold text-lg"
            >
              Search Doctors
            </button>
          </form>
        </div>

        {/* Quick Specializations */}
        <div className="mt-16">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Popular Specializations
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              { name: 'Cardiology', icon: '❤️' },
              { name: 'Dentistry', icon: '🦷' },
              { name: 'Dermatology', icon: '🧴' },
              { name: 'Orthopedics', icon: '🦴' },
              { name: 'Pediatrics', icon: '👶' },
              { name: 'General Medicine', icon: '🏥' },
            ].map((specialty) => (
              <Link
                key={specialty.name}
                href={`/doctors?specialization=${specialty.name}`}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 text-center cursor-pointer border border-gray-200"
              >
                <div className="text-4xl mb-2">{specialty.icon}</div>
                <div className="text-sm font-semibold text-gray-900">
                  {specialty.name}
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🔍</span>
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">
              Find Top Doctors
            </h4>
            <p className="text-gray-600">
              Browse through verified doctors across all specializations
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">📅</span>
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">
              Book Instantly
            </h4>
            <p className="text-gray-600">
              Check real-time availability and book appointments in seconds
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">📱</span>
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">
              Manage Appointments
            </h4>
            <p className="text-gray-600">
              View and manage all your appointments in one place
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h5 className="text-lg font-semibold mb-4">DocAssist</h5>
              <p className="text-gray-400">
                Your trusted partner for healthcare appointments
              </p>
            </div>
            <div>
              <h5 className="text-lg font-semibold mb-4">Quick Links</h5>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="/doctors" className="hover:text-white">
                    Find Doctors
                  </Link>
                </li>
                <li>
                  <Link href="/appointments" className="hover:text-white">
                    My Appointments
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h5 className="text-lg font-semibold mb-4">Contact</h5>
              <p className="text-gray-400">
                support@docassist.com
              </p>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            © 2026 DocAssist Practice Manager. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
