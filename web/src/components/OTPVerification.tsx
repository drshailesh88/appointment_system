'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api-client';

interface OTPVerificationProps {
  onSuccess: () => void;
  onCancel?: () => void;
}

export default function OTPVerification({ onSuccess, onCancel }: OTPVerificationProps) {
  const [phone, setPhone] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number | null>(null);

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.sendOTP(phone);
      setOtpSent(true);
      setExpiresIn(response.expires_in_seconds);
    } catch (err: any) {
      setError(err.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await apiClient.verifyOTP(phone, otpCode);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-md mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {otpSent ? 'Verify OTP' : 'Login with Phone'}
      </h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {!otpSent ? (
        <form onSubmit={handleSendOTP}>
          <div className="mb-4">
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number
            </label>
            <input
              type="tel"
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Enter your phone number"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
              pattern="[0-9]{10,15}"
            />
            <p className="text-sm text-gray-500 mt-1">
              We'll send you a verification code
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading || !phone}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {loading ? 'Sending...' : 'Send OTP'}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      ) : (
        <form onSubmit={handleVerifyOTP}>
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-4">
              Enter the 6-digit code sent to <strong>{phone}</strong>
            </p>
            <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2">
              OTP Code
            </label>
            <input
              type="text"
              id="otp"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-2xl tracking-widest"
              required
              pattern="[0-9]{6}"
              maxLength={6}
            />
            {expiresIn && (
              <p className="text-sm text-gray-500 mt-1">
                Code expires in {Math.floor(expiresIn / 60)} minutes
              </p>
            )}
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading || otpCode.length !== 6}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {loading ? 'Verifying...' : 'Verify OTP'}
            </button>
            <button
              type="button"
              onClick={() => {
                setOtpSent(false);
                setOtpCode('');
                setError(null);
              }}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Change Number
            </button>
          </div>

          <button
            type="button"
            onClick={handleSendOTP}
            disabled={loading}
            className="w-full mt-4 text-sm text-blue-600 hover:text-blue-700 disabled:text-gray-400"
          >
            Resend OTP
          </button>
        </form>
      )}
    </div>
  );
}
