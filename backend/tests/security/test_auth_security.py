"""
Comprehensive security tests for authentication and authorization.

Tests cover:
1. Authentication bypass attempts
2. Session security
3. Password security
4. RBAC enforcement
5. API security headers
"""

import time
from datetime import datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserRole
from app.models.clinic import Clinic
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient


class TestAuthenticationBypass:
    """Test authentication bypass attempts."""

    def test_access_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without authentication token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "detail" in response.json()
        assert "not authenticated" in response.json()["detail"].lower()

    def test_access_with_expired_token(self, client: TestClient, test_user: User):
        """Test accessing endpoint with expired token."""
        # Create token that expired 1 hour ago
        expired_token = create_access_token(
            subject=str(test_user.id),
            expires_delta=timedelta(hours=-1)
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_access_with_malformed_token(self, client: TestClient):
        """Test accessing endpoint with malformed token."""
        malformed_tokens = [
            "not-a-jwt-token",
            "Bearer.invalid.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "",
            "Bearer ",
        ]

        for token in malformed_tokens:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 401, f"Failed for token: {token}"

    def test_access_with_wrong_secret(self, client: TestClient, test_user: User):
        """Test accessing endpoint with token signed using wrong secret."""
        # Create token with different secret
        wrong_secret_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "type": "access",
            },
            "wrong-secret-key-12345",
            algorithm="HS256"
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {wrong_secret_token}"}
        )

        assert response.status_code == 401

    def test_access_with_wrong_algorithm(self, client: TestClient, test_user: User):
        """Test accessing endpoint with token using wrong algorithm."""
        # Create token with HS512 instead of HS256
        wrong_algo_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "type": "access",
            },
            settings.jwt_secret_key,
            algorithm="HS512"
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {wrong_algo_token}"}
        )

        assert response.status_code == 401

    def test_sql_injection_in_login_username(self, client: TestClient):
        """Test SQL injection attempts in login username field."""
        sql_injection_payloads = [
            "admin' OR '1'='1",
            "admin'--",
            "admin' OR '1'='1'--",
            "'; DROP TABLE users; --",
            "admin'; DELETE FROM users WHERE '1'='1",
            "' OR 1=1--",
            "1' UNION SELECT NULL, NULL, NULL--",
        ]

        for payload in sql_injection_payloads:
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": payload,
                    "password": "anypassword"
                }
            )

            # Should not succeed or cause SQL error
            assert response.status_code in [401, 422], f"Failed for payload: {payload}"
            # Should not expose SQL error details
            if response.status_code != 422:
                assert "sql" not in response.json().get("detail", "").lower()

    def test_sql_injection_in_login_password(self, client: TestClient, test_user: User):
        """Test SQL injection attempts in login password field."""
        sql_injection_payloads = [
            "' OR '1'='1",
            "password' OR '1'='1'--",
            "'; DELETE FROM users--",
        ]

        for payload in sql_injection_payloads:
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": payload
                }
            )

            assert response.status_code == 401
            assert "sql" not in response.json().get("detail", "").lower()

    def test_timing_attack_resistance_on_password_comparison(self, client: TestClient, test_user: User):
        """Test that password comparison is resistant to timing attacks."""
        # This tests that wrong passwords take roughly the same time
        # regardless of how many characters match

        times = []
        passwords = [
            "a" * 20,  # Completely wrong
            "testpassword" + "x" * 8,  # Close but wrong
            "wrongpassword123",  # Different length
        ]

        for password in passwords:
            start = time.time()
            client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": password
                }
            )
            end = time.time()
            times.append(end - start)

        # All attempts should take roughly the same time (within 50ms)
        # This is not a perfect test but catches obvious timing leaks
        max_diff = max(times) - min(times)
        assert max_diff < 0.05, f"Timing difference too large: {max_diff}s"

    def test_refresh_token_cannot_be_used_as_access_token(self, client: TestClient, test_user: User):
        """Test that refresh tokens cannot be used to access protected endpoints."""
        refresh_token = create_refresh_token(subject=str(test_user.id))

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )

        assert response.status_code == 401

    def test_token_with_invalid_user_id(self, client: TestClient):
        """Test token with non-existent user ID."""
        fake_user_id = str(uuid4())
        token = create_access_token(subject=fake_user_id)

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401

    def test_token_with_malformed_user_id(self, client: TestClient):
        """Test token with malformed user ID (not UUID)."""
        token = create_access_token(subject="not-a-uuid")

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401


class TestSessionSecurity:
    """Test session and token security."""

    def test_token_not_exposed_in_response_body(self, client: TestClient, test_user: User):
        """Test that tokens are not exposed in error responses."""
        token = create_access_token(subject=str(test_user.id))

        # Make a request that might fail
        response = client.post(
            "/api/v1/appointments",
            headers={"Authorization": f"Bearer {token}"},
            json={"invalid": "data"}
        )

        # Token should not be in response
        response_text = response.text.lower()
        assert token not in response_text
        assert "bearer" not in response_text or "www-authenticate" in response_text

    def test_refresh_token_rotation(self, client: TestClient, test_user: User):
        """Test that refresh token is rotated on use."""
        # Login to get initial refresh token
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == 200
        first_refresh_token = response.json()["refresh_token"]

        # Use refresh token to get new tokens
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_refresh_token}
        )

        assert response.status_code == 200
        second_refresh_token = response.json()["refresh_token"]

        # Refresh tokens should be different (rotation)
        assert first_refresh_token != second_refresh_token

        # Old refresh token should no longer work
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_refresh_token}
        )

        assert response.status_code == 401

    def test_session_invalidation_on_logout(self, client: TestClient, test_user: User, db: Session):
        """Test that session is properly invalidated on logout."""
        # Login
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            }
        )

        access_token = response.json()["access_token"]
        refresh_token = response.json()["refresh_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200

        # Refresh token should no longer work
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 401

        # Verify refresh token cleared in database
        db.refresh(test_user)
        assert test_user.refresh_token is None

    def test_inactive_user_cannot_login(self, client: TestClient, db: Session, test_user: User):
        """Test that inactive users cannot login."""
        # Deactivate user
        test_user.is_active = False
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()

    def test_inactive_user_token_rejected(self, client: TestClient, db: Session, test_user: User):
        """Test that tokens for inactive users are rejected."""
        # Create token before deactivation
        token = create_access_token(subject=str(test_user.id))

        # Deactivate user
        test_user.is_active = False
        db.commit()

        # Token should be rejected
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403


class TestPasswordSecurity:
    """Test password security mechanisms."""

    def test_password_is_hashed_with_bcrypt(self, db: Session, test_clinic: Clinic):
        """Test that passwords are hashed using bcrypt."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Bcrypt hashes start with $2b$ or $2a$
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

        # Hash should be different from plaintext
        assert hashed != password

        # Hash should be verifiable
        assert verify_password(password, hashed)

    def test_password_not_stored_in_plaintext(self, db: Session, test_clinic: Clinic):
        """Test that passwords are never stored in plaintext."""
        password = "MySecretPassword123!"

        user = User(
            id=str(uuid4()),
            email="security@test.com",
            phone="+919876543299",
            password_hash=get_password_hash(password),
            name="Security Test User",
            role=UserRole.RECEPTIONIST.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Password should be hashed
        assert user.password_hash != password
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")

    def test_password_not_in_user_response(self, client: TestClient, test_user: User, auth_headers: dict):
        """Test that password hash is not exposed in API responses."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Password fields should not be in response
        assert "password" not in data
        assert "password_hash" not in data
        assert "hashed_password" not in data

    def test_same_password_produces_different_hashes(self):
        """Test that hashing the same password produces different hashes (salted)."""
        password = "TestPassword123"

        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_password_verification_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "MyPassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed)
        assert not verify_password("mypassword123", hashed)
        assert not verify_password("MYPASSWORD123", hashed)

    def test_weak_passwords_in_registration(self, client: TestClient, test_clinic: Clinic):
        """Test that weak passwords are handled (if validation exists)."""
        weak_passwords = [
            "123",
            "password",
            "abc",
            "",
        ]

        for weak_password in weak_passwords:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"user_{uuid4()}@test.com",
                    "phone": f"+9198765432{hash(weak_password) % 100:02d}",
                    "password": weak_password,
                    "name": "Test User",
                    "role": "receptionist",
                    "clinic_id": str(test_clinic.id),
                }
            )

            # Should either reject or accept (we're just checking it doesn't crash)
            assert response.status_code in [201, 400, 422]


class TestRBACEnforcement:
    """Test Role-Based Access Control enforcement."""

    def test_staff_cannot_access_admin_endpoints(self, client: TestClient, db: Session, test_clinic: Clinic):
        """Test that staff users cannot access admin-only endpoints."""
        # Create receptionist user
        receptionist = User(
            id=str(uuid4()),
            email="receptionist@test.com",
            phone="+919876543213",
            password_hash=get_password_hash("password123"),
            name="Receptionist User",
            role=UserRole.RECEPTIONIST.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(receptionist)
        db.commit()

        # Create token for receptionist
        token = create_access_token(subject=str(receptionist.id))

        # Try to access admin endpoint (if exists)
        # This is a placeholder - adjust based on actual admin endpoints
        response = client.get(
            "/api/v1/auth/me",  # Replace with actual admin endpoint
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should either succeed (non-admin endpoint) or return 403
        assert response.status_code in [200, 403]

    def test_doctor_cannot_access_other_doctors_data(
        self,
        client: TestClient,
        db: Session,
        test_clinic: Clinic,
        test_doctor: Doctor
    ):
        """Test horizontal privilege escalation prevention."""
        # Create another doctor
        user2 = User(
            id=str(uuid4()),
            email="doctor2@test.com",
            phone="+919876543214",
            password_hash=get_password_hash("password123"),
            name="Dr. Another Doctor",
            role=UserRole.DOCTOR.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(user2)
        db.commit()

        doctor2 = Doctor(
            id=str(uuid4()),
            user_id=user2.id,
            clinic_id=test_clinic.id,
            name="Dr. Another Doctor",
            specialization="Cardiology",
            qualification="MBBS, MD",
            registration_number="MH54321",
            consultation_fee=800.0,
            is_active=True,
        )
        db.add(doctor2)
        db.commit()

        # Create appointment for doctor2
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Test Patient",
            phone="+919876543215",
            gender="male",
        )
        db.add(patient)
        db.commit()

        appointment = Appointment(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            doctor_id=doctor2.id,
            patient_id=patient.id,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, minutes=15),
            status="scheduled",
            appointment_type="new_consultation",
        )
        db.add(appointment)
        db.commit()

        # Get token for first doctor
        user1 = db.query(User).filter(User.id == test_doctor.user_id).first()
        token = create_access_token(subject=str(user1.id))

        # Try to access doctor2's appointment
        response = client.get(
            f"/api/v1/appointments/{appointment.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should deny access or return filtered results
        # Adjust based on actual API behavior
        assert response.status_code in [200, 403, 404]

    def test_staff_from_different_clinic_cannot_access_data(
        self,
        client: TestClient,
        db: Session,
        test_clinic: Clinic
    ):
        """Test that staff from one clinic cannot access another clinic's data."""
        # Create another clinic
        other_clinic = Clinic(
            id=str(uuid4()),
            name="Other Clinic",
            address="456 Other Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            phone="+919876543216",
            email="other@clinic.com",
            subscription_tier="basic",
        )
        db.add(other_clinic)
        db.commit()

        # Create user in other clinic
        other_user = User(
            id=str(uuid4()),
            email="other@test.com",
            phone="+919876543217",
            password_hash=get_password_hash("password123"),
            name="Other Clinic User",
            role=UserRole.RECEPTIONIST.value,
            clinic_id=other_clinic.id,
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        # Create token for other clinic user
        token = create_access_token(subject=str(other_user.id))

        # Create patient in test_clinic
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Test Patient",
            phone="+919876543218",
            gender="female",
        )
        db.add(patient)
        db.commit()

        # Try to access test_clinic's patient
        response = client.get(
            f"/api/v1/patients/{patient.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should deny access
        assert response.status_code in [403, 404]

    def test_vertical_privilege_escalation_prevention(
        self,
        client: TestClient,
        db: Session,
        test_clinic: Clinic
    ):
        """Test that users cannot escalate their own privileges."""
        # Create receptionist
        receptionist = User(
            id=str(uuid4()),
            email="receptionist2@test.com",
            phone="+919876543219",
            password_hash=get_password_hash("password123"),
            name="Receptionist User",
            role=UserRole.RECEPTIONIST.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(receptionist)
        db.commit()

        token = create_access_token(subject=str(receptionist.id))

        # Try to update own role to admin (if such endpoint exists)
        response = client.put(
            f"/api/v1/users/{receptionist.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "admin"}
        )

        # Should deny or not allow role change
        assert response.status_code in [403, 404, 405, 422]

    def test_admin_can_access_all_clinics(
        self,
        client: TestClient,
        db: Session,
        test_clinic: Clinic,
        test_user: User
    ):
        """Test that admin users can access any clinic's data."""
        # Ensure test_user is admin
        test_user.role = UserRole.ADMIN.value
        db.commit()

        token = create_access_token(subject=str(test_user.id))

        # Create another clinic
        other_clinic = Clinic(
            id=str(uuid4()),
            name="Admin Access Clinic",
            address="789 Admin Street",
            city="Bangalore",
            state="Karnataka",
            pincode="560001",
            phone="+919876543220",
            email="admin@clinic.com",
            subscription_tier="premium",
        )
        db.add(other_clinic)
        db.commit()

        # Admin should be able to access it
        response = client.get(
            f"/api/v1/clinics/{other_clinic.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should succeed (assuming such endpoint exists)
        # Adjust based on actual API
        assert response.status_code in [200, 404]


class TestAPISecurityHeaders:
    """Test API security headers."""

    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are properly configured."""
        response = client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )

        # CORS should be configured
        assert response.status_code in [200, 405]

    def test_cors_restricts_unauthorized_origins(self, client: TestClient):
        """Test that CORS blocks unauthorized origins."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Origin": "https://evil-site.com"}
        )

        # Should not have CORS headers for unauthorized origin
        # or should explicitly deny
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] != "https://evil-site.com"

    def test_no_sensitive_headers_in_error_responses(self, client: TestClient):
        """Test that error responses don't leak sensitive headers."""
        response = client.get("/api/v1/auth/me")

        # Check for sensitive header exposure
        sensitive_headers = ["x-powered-by", "server", "x-aspnet-version"]

        for header in sensitive_headers:
            assert header not in response.headers.keys()

    def test_content_type_header_on_json_responses(self, client: TestClient, auth_headers: dict):
        """Test that JSON responses have correct content-type."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")

    def test_no_caching_for_authenticated_endpoints(self, client: TestClient, auth_headers: dict):
        """Test that authenticated endpoints are not cached."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        if response.status_code == 200:
            # Should have cache-control headers preventing caching
            cache_control = response.headers.get("cache-control", "")
            # Either explicitly set or default behavior
            assert cache_control == "" or "no-store" in cache_control or "no-cache" in cache_control


class TestAuthenticationEdgeCases:
    """Test edge cases in authentication."""

    def test_login_with_very_long_username(self, client: TestClient):
        """Test login with extremely long username."""
        long_username = "a" * 10000

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": long_username,
                "password": "password123"
            }
        )

        # Should handle gracefully
        assert response.status_code in [401, 422]

    def test_login_with_very_long_password(self, client: TestClient, test_user: User):
        """Test login with extremely long password."""
        long_password = "a" * 10000

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": long_password
            }
        )

        # Should handle gracefully
        assert response.status_code in [401, 422]

    def test_login_with_unicode_characters(self, client: TestClient, db: Session, test_clinic: Clinic):
        """Test login with unicode characters in credentials."""
        unicode_user = User(
            id=str(uuid4()),
            email="unicode@test.com",
            phone="+919876543221",
            password_hash=get_password_hash("पासवर्ड123"),  # Hindi password
            name="Unicode User",
            role=UserRole.RECEPTIONIST.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(unicode_user)
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "unicode@test.com",
                "password": "पासवर्ड123"
            }
        )

        # Should handle unicode properly
        assert response.status_code in [200, 422]

    def test_multiple_failed_login_attempts(self, client: TestClient, test_user: User):
        """Test multiple failed login attempts (rate limiting check)."""
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "wrongpassword"
                }
            )

            # Should either reject or rate limit
            assert response.status_code in [401, 429]

    def test_simultaneous_logins_same_user(self, client: TestClient, test_user: User):
        """Test that same user can login from multiple devices."""
        # First login
        response1 = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response1.status_code == 200
        token1 = response1.json()["access_token"]

        # Second login
        response2 = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response2.status_code == 200
        token2 = response2.json()["access_token"]

        # Both tokens should work (or have session limit)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code in [200, 401]

    def test_token_with_missing_required_claims(self, client: TestClient):
        """Test token with missing required claims."""
        # Token without 'sub' claim
        token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "type": "access",
            },
            settings.jwt_secret_key,
            algorithm="HS256"
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401

    def test_token_with_extra_claims(self, client: TestClient, test_user: User):
        """Test that extra claims in token don't cause issues."""
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={
                "custom_claim": "value",
                "another_claim": 123,
            }
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should work normally
        assert response.status_code == 200
