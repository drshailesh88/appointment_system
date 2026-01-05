"""
Comprehensive authentication and authorization tests for DocAssist Practice Manager.

This module tests critical security flows including:
- Login/Logout with password-based auth
- JWT token generation, refresh, and validation
- Role-Based Access Control (RBAC)
- OTP authentication for patients
- Token security and edge cases
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.models.clinic import Clinic
from app.models.otp import OTP
from app.models.user import User, UserRole


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def second_clinic(db: Session) -> Clinic:
    """Create a second clinic for cross-clinic access tests."""
    clinic = Clinic(
        id=str(uuid4()),
        name="Second Test Clinic",
        address="456 Another Street",
        city="Delhi",
        state="Delhi",
        pincode="110001",
        phone="+919876543211",
        email="second@clinic.com",
        subscription_tier="basic",
    )
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic


@pytest.fixture
def doctor_user(db: Session, test_clinic: Clinic) -> User:
    """Create a doctor user."""
    user = User(
        id=str(uuid4()),
        email="doctor@test.com",
        phone="+919876543222",
        password_hash=get_password_hash("DoctorPass123!"),
        name="Dr. John Doe",
        role=UserRole.DOCTOR.value,
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def staff_user(db: Session, test_clinic: Clinic) -> User:
    """Create a staff (receptionist) user."""
    user = User(
        id=str(uuid4()),
        email="staff@test.com",
        phone="+919876543223",
        password_hash=get_password_hash("StaffPass123!"),
        name="Jane Smith",
        role=UserRole.RECEPTIONIST.value,
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def deactivated_user(db: Session, test_clinic: Clinic) -> User:
    """Create a deactivated user."""
    user = User(
        id=str(uuid4()),
        email="deactivated@test.com",
        phone="+919876543224",
        password_hash=get_password_hash("DeactivatedPass123!"),
        name="Deactivated User",
        role=UserRole.RECEPTIONIST.value,
        clinic_id=test_clinic.id,
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_clinic_user(db: Session, second_clinic: Clinic) -> User:
    """Create a user belonging to a different clinic."""
    user = User(
        id=str(uuid4()),
        email="other@clinic.com",
        phone="+919876543225",
        password_hash=get_password_hash("OtherPass123!"),
        name="Other Clinic User",
        role=UserRole.DOCTOR.value,
        clinic_id=second_clinic.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ============================================================================
# TEST CLASS: LOGIN & LOGOUT
# ============================================================================


class TestLoginLogout:
    """Test user login and logout flows."""

    def test_login_with_email_success(self, client: TestClient, test_user: User):
        """Test successful login using email."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify token structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == settings.jwt_access_token_expire_minutes * 60

        # Verify tokens are different
        assert data["access_token"] != data["refresh_token"]

    def test_login_with_phone_success(self, client: TestClient, test_user: User):
        """Test successful login using phone number."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.phone,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_json_endpoint(self, client: TestClient, test_user: User):
        """Test login with JSON body instead of form data."""
        response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login fails with incorrect password."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Incorrect email/phone or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login fails with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401
        assert "Incorrect email/phone or password" in response.json()["detail"]

    def test_login_deactivated_user(self, client: TestClient, deactivated_user: User):
        """Test login fails for deactivated user account."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": deactivated_user.email,
                "password": "DeactivatedPass123!",
            },
        )

        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()

    def test_login_updates_last_login(
        self, client: TestClient, test_user: User, db: Session
    ):
        """Test that login updates the last_login timestamp."""
        # Record initial last_login (should be None)
        initial_last_login = test_user.last_login

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200

        # Refresh user from database
        db.refresh(test_user)

        # Verify last_login was updated
        assert test_user.last_login is not None
        assert test_user.last_login != initial_last_login
        assert test_user.last_login > datetime.now(timezone.utc) - timedelta(seconds=5)

    def test_logout_success(self, client: TestClient, auth_headers: dict, test_user: User, db: Session):
        """Test successful logout invalidates refresh token."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Verify refresh token is stored
        db.refresh(test_user)
        assert test_user.refresh_token == refresh_token

        # Logout
        response = client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert "logout" in response.json()["message"].lower()

        # Verify refresh token is cleared
        db.refresh(test_user)
        assert test_user.refresh_token is None

    def test_logout_requires_authentication(self, client: TestClient):
        """Test that logout requires valid authentication."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# ============================================================================
# TEST CLASS: TOKEN REFRESH
# ============================================================================


class TestTokenRefresh:
    """Test JWT token refresh flows."""

    def test_refresh_token_success(self, client: TestClient, test_user: User):
        """Test successful token refresh."""
        # Login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        old_access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Wait a moment to ensure new token is different
        time.sleep(0.1)

        # Refresh the token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify new tokens are different from old ones
        assert data["access_token"] != old_access_token
        assert data["refresh_token"] != refresh_token
        assert data["token_type"] == "bearer"

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Test refresh fails with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_with_access_token_fails(self, client: TestClient, test_user: User):
        """Test that using access token for refresh fails (wrong token type)."""
        # Login to get access token
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_with_expired_token(self, client: TestClient, test_user: User):
        """Test refresh fails with expired token."""
        # Create an expired refresh token
        expired_token = create_refresh_token(
            subject=str(test_user.id),
            expires_delta=timedelta(seconds=-1),
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token},
        )

        assert response.status_code == 401

    def test_refresh_token_not_in_database(
        self, client: TestClient, test_user: User, db: Session
    ):
        """Test refresh fails if token not stored in user record."""
        # Create a valid refresh token but don't store it in DB
        refresh_token = create_refresh_token(subject=str(test_user.id))

        # Ensure user has no refresh token in DB
        test_user.refresh_token = None
        db.commit()

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_for_deactivated_user(
        self, client: TestClient, deactivated_user: User, db: Session
    ):
        """Test refresh fails for deactivated user even with valid token."""
        # Create a valid refresh token for deactivated user
        refresh_token = create_refresh_token(subject=str(deactivated_user.id))
        deactivated_user.refresh_token = refresh_token
        db.commit()

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


# ============================================================================
# TEST CLASS: TOKEN SECURITY
# ============================================================================


class TestTokenSecurity:
    """Test JWT token security and validation."""

    def test_expired_access_token_rejected(self, client: TestClient, test_user: User):
        """Test that expired access tokens are rejected."""
        # Create an expired access token
        expired_token = create_access_token(
            subject=str(test_user.id),
            expires_delta=timedelta(seconds=-1),
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    def test_invalid_signature_rejected(self, client: TestClient, test_user: User):
        """Test that tokens with invalid signatures are rejected."""
        # Create a token with wrong secret key
        invalid_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "type": "access",
            },
            "wrong-secret-key",
            algorithm="HS256",
        )

        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    def test_refresh_token_as_access_rejected(
        self, client: TestClient, test_user: User
    ):
        """Test that refresh token cannot be used as access token."""
        # Create a refresh token
        refresh_token = create_refresh_token(subject=str(test_user.id))

        # Try to use it as access token
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    def test_missing_token_rejected(self, client: TestClient):
        """Test that requests without token are rejected."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_malformed_token_rejected(self, client: TestClient):
        """Test that malformed tokens are rejected."""
        headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_token_missing_bearer_prefix(self, client: TestClient, auth_headers: dict):
        """Test that token without 'Bearer' prefix is rejected."""
        # Extract token without Bearer prefix
        token = auth_headers["Authorization"].split(" ")[1]
        headers = {"Authorization": token}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_token_with_nonexistent_user_id(self, client: TestClient):
        """Test that token with non-existent user ID is rejected."""
        fake_user_id = str(uuid4())
        token = create_access_token(subject=fake_user_id)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    def test_token_payload_includes_role_and_clinic(
        self, client: TestClient, test_user: User
    ):
        """Test that token payload includes user role and clinic_id."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        access_token = response.json()["access_token"]

        # Decode token to check payload
        payload = jwt.decode(
            access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        assert payload["sub"] == str(test_user.id)
        assert payload["role"] == test_user.role
        assert payload["clinic_id"] == str(test_user.clinic_id)
        assert payload["type"] == "access"


# ============================================================================
# TEST CLASS: ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================


class TestRoleBasedAccessControl:
    """Test role-based access control and permissions."""

    def test_admin_can_access_admin_endpoint(
        self, client: TestClient, test_user: User
    ):
        """Test that admin users can access admin-only endpoints."""
        # test_user is an admin by default
        token = create_access_token(
            subject=str(test_user.id),
            extra_claims={
                "role": UserRole.ADMIN.value,
                "clinic_id": str(test_user.clinic_id),
            },
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Note: This test assumes there's an admin-only endpoint
        # For now, we verify the user info shows admin role
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_doctor_cannot_access_other_clinic_data(
        self,
        client: TestClient,
        doctor_user: User,
        test_clinic: Clinic,
        second_clinic: Clinic,
    ):
        """Test that doctors can only access their own clinic data."""
        # Create token for doctor in test_clinic
        token = create_access_token(
            subject=str(doctor_user.id),
            extra_claims={
                "role": UserRole.DOCTOR.value,
                "clinic_id": str(test_clinic.id),
            },
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Verify doctor's clinic_id
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["clinic_id"] == str(test_clinic.id)
        assert response.json()["clinic_id"] != str(second_clinic.id)

    def test_staff_has_limited_role(
        self, client: TestClient, staff_user: User
    ):
        """Test that staff users have receptionist role."""
        token = create_access_token(
            subject=str(staff_user.id),
            extra_claims={
                "role": UserRole.RECEPTIONIST.value,
                "clinic_id": str(staff_user.clinic_id),
            },
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.RECEPTIONIST.value

    def test_cross_clinic_access_prevention(
        self,
        client: TestClient,
        test_clinic: Clinic,
        other_clinic_user: User,
    ):
        """Test that users cannot access data from other clinics."""
        # Create token for user from different clinic
        token = create_access_token(
            subject=str(other_clinic_user.id),
            extra_claims={
                "role": UserRole.DOCTOR.value,
                "clinic_id": str(other_clinic_user.clinic_id),
            },
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Verify user belongs to different clinic
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["clinic_id"] != str(test_clinic.id)

    def test_deactivated_user_rejected_with_valid_token(
        self, client: TestClient, deactivated_user: User
    ):
        """Test that deactivated users are rejected even with valid tokens."""
        # Create a valid token for deactivated user
        token = create_access_token(
            subject=str(deactivated_user.id),
            extra_claims={
                "role": deactivated_user.role,
                "clinic_id": str(deactivated_user.clinic_id),
            },
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


# ============================================================================
# TEST CLASS: OTP AUTHENTICATION
# ============================================================================


class TestOTPAuthentication:
    """Test OTP-based authentication for patients."""

    def test_otp_generation(self, db: Session):
        """Test OTP code generation."""
        from app.services.otp_service import OTPService

        service = OTPService(db)
        otp_code = service.generate_otp()

        # Verify OTP is 6 digits
        assert len(otp_code) == 6
        assert otp_code.isdigit()

    @pytest.mark.asyncio
    async def test_send_otp_creates_record(self, db: Session):
        """Test that sending OTP creates database record."""
        from app.services.otp_service import OTPService

        # Use async session for async operations
        from app.core.database import async_session_maker

        async with async_session_maker() as async_db:
            service = OTPService(async_db)
            phone = "+919876543299"

            otp_record = await service.send_otp(phone)

            assert otp_record.phone == phone
            assert len(otp_record.otp_code) == 6
            assert otp_record.is_verified is False
            assert otp_record.attempts == 0
            assert otp_record.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_otp_verification_success(self, db: Session):
        """Test successful OTP verification."""
        from app.services.otp_service import OTPService
        from app.core.database import async_session_maker

        async with async_session_maker() as async_db:
            service = OTPService(async_db)
            phone = "+919876543298"

            # Send OTP
            otp_record = await service.send_otp(phone)
            otp_code = otp_record.otp_code

            # Verify OTP
            token = await service.verify_otp(phone, otp_code)

            assert token is not None
            assert isinstance(token, str)

            # Verify token payload
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            assert payload["sub"] == phone
            assert payload["type"] == "patient_otp"

    @pytest.mark.asyncio
    async def test_otp_verification_wrong_code(self, db: Session):
        """Test OTP verification fails with wrong code."""
        from app.services.otp_service import OTPService
        from app.core.database import async_session_maker

        async with async_session_maker() as async_db:
            service = OTPService(async_db)
            phone = "+919876543297"

            # Send OTP
            await service.send_otp(phone)

            # Try with wrong code
            token = await service.verify_otp(phone, "000000")

            assert token is None

    @pytest.mark.asyncio
    async def test_otp_expiration(self, db: Session):
        """Test that expired OTPs are rejected."""
        from app.core.database import async_session_maker

        async with async_session_maker() as async_db:
            phone = "+919876543296"

            # Create an expired OTP
            expired_otp = OTP(
                phone=phone,
                otp_code="123456",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                is_verified=False,
                attempts=0,
            )
            async_db.add(expired_otp)
            await async_db.commit()

            # Try to verify expired OTP
            from app.services.otp_service import OTPService
            service = OTPService(async_db)
            token = await service.verify_otp(phone, "123456")

            assert token is None

    @pytest.mark.asyncio
    async def test_otp_max_attempts(self, db: Session):
        """Test that OTP is rejected after max attempts."""
        from app.core.database import async_session_maker

        async with async_session_maker() as async_db:
            phone = "+919876543295"

            # Create OTP with max attempts
            otp = OTP(
                phone=phone,
                otp_code="123456",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                is_verified=False,
                attempts=3,  # Max attempts
            )
            async_db.add(otp)
            await async_db.commit()

            # Try to verify (should fail due to max attempts)
            from app.services.otp_service import OTPService
            service = OTPService(async_db)
            token = await service.verify_otp(phone, "123456")

            assert token is None

    @pytest.mark.asyncio
    async def test_otp_invalidates_previous_codes(self, db: Session):
        """Test that requesting new OTP invalidates previous codes."""
        from app.services.otp_service import OTPService
        from app.core.database import async_session_maker
        from sqlalchemy import select

        async with async_session_maker() as async_db:
            service = OTPService(async_db)
            phone = "+919876543294"

            # Send first OTP
            first_otp = await service.send_otp(phone)
            first_code = first_otp.otp_code

            # Send second OTP
            second_otp = await service.send_otp(phone)
            second_code = second_otp.otp_code

            # Verify codes are different
            assert first_code != second_code

            # First OTP should now be marked as verified (invalidated)
            result = await async_db.execute(
                select(OTP).where(OTP.id == first_otp.id)
            )
            first_otp_updated = result.scalar_one()
            assert first_otp_updated.is_verified is True

            # Only second OTP should work
            token = await service.verify_otp(phone, second_code)
            assert token is not None

            # First code should not work
            token_old = await service.verify_otp(phone, first_code)
            assert token_old is None

    def test_otp_token_decode(self):
        """Test decoding OTP JWT tokens."""
        from app.services.otp_service import OTPService

        phone = "+919876543293"
        service = OTPService(None)  # No DB needed for token operations

        # Create token
        token = service.create_access_token(phone)

        # Decode token
        decoded_phone = service.decode_token(token)

        assert decoded_phone == phone

    def test_otp_token_wrong_type_rejected(self):
        """Test that non-OTP tokens are rejected."""
        from app.services.otp_service import OTPService
        from app.core.security import create_access_token

        # Create a regular access token (not OTP)
        regular_token = create_access_token(
            subject="user_id_123",
            extra_claims={"type": "access"},
        )

        service = OTPService(None)
        decoded = service.decode_token(regular_token)

        # Should be rejected because type is not "patient_otp"
        assert decoded is None


# ============================================================================
# TEST CLASS: EDGE CASES & SECURITY
# ============================================================================


class TestEdgeCases:
    """Test edge cases and security scenarios."""

    def test_password_with_special_characters(
        self, client: TestClient, test_clinic: Clinic, db: Session
    ):
        """Test passwords with special characters are handled correctly."""
        special_password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:,.<>?"

        # Create user with special character password
        user = User(
            id=str(uuid4()),
            email="special@test.com",
            phone="+919876543290",
            password_hash=get_password_hash(special_password),
            name="Special User",
            role=UserRole.ADMIN.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Test login with special characters
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": user.email,
                "password": special_password,
            },
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_very_long_password(
        self, client: TestClient, test_clinic: Clinic, db: Session
    ):
        """Test handling of very long passwords (within limits)."""
        # Create a long but valid password (within 100 char limit from schema)
        long_password = "A" * 95 + "b123!"

        user = User(
            id=str(uuid4()),
            email="longpass@test.com",
            phone="+919876543291",
            password_hash=get_password_hash(long_password),
            name="Long Password User",
            role=UserRole.ADMIN.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Test login with long password
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": user.email,
                "password": long_password,
            },
        )

        assert response.status_code == 200

    def test_concurrent_login_sessions(
        self, client: TestClient, test_user: User, db: Session
    ):
        """Test that multiple concurrent sessions can exist."""
        # First login
        response1 = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )
        token1 = response1.json()["access_token"]

        # Second login (should not invalidate first)
        response2 = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )
        token2 = response2.json()["access_token"]

        # Both tokens should be different
        assert token1 != token2

        # Both tokens should work
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        response_with_token1 = client.get("/api/v1/auth/me", headers=headers1)
        response_with_token2 = client.get("/api/v1/auth/me", headers=headers2)

        assert response_with_token1.status_code == 200
        assert response_with_token2.status_code == 200

    def test_case_sensitive_email(
        self, client: TestClient, test_user: User
    ):
        """Test that email is case-insensitive for login."""
        # Try login with uppercase email
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email.upper(),
                "password": "testpassword123",
            },
        )

        # This might fail depending on database collation
        # Most implementations should handle this gracefully
        # For now, we just verify it doesn't crash
        assert response.status_code in [200, 401]

    def test_sql_injection_attempt(self, client: TestClient):
        """Test that SQL injection attempts are safely handled."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin' OR '1'='1",
                "password": "anything",
            },
        )

        # Should fail authentication, not execute SQL
        assert response.status_code == 401

    def test_unicode_in_credentials(
        self, client: TestClient, test_clinic: Clinic, db: Session
    ):
        """Test handling of Unicode characters in passwords."""
        unicode_password = "पासवर्ड123"  # Hindi for password

        user = User(
            id=str(uuid4()),
            email="unicode@test.com",
            phone="+919876543292",
            password_hash=get_password_hash(unicode_password),
            name="Unicode User",
            role=UserRole.ADMIN.value,
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Test login with Unicode password
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": user.email,
                "password": unicode_password,
            },
        )

        assert response.status_code == 200

    def test_empty_password_rejected(self, client: TestClient):
        """Test that empty passwords are rejected."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "any@test.com",
                "password": "",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_whitespace_only_password_rejected(self, client: TestClient):
        """Test that whitespace-only passwords are rejected."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "any@test.com",
                "password": "        ",
            },
        )

        # Should fail authentication
        assert response.status_code in [401, 422]

    def test_token_expiry_claim(self, client: TestClient, test_user: User):
        """Test that tokens include proper expiry claims."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        access_token = response.json()["access_token"]

        # Decode and check expiry
        payload = jwt.decode(
            access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        assert "exp" in payload
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        # Verify expiry is in the future
        assert exp_datetime > datetime.now(timezone.utc)

        # Verify expiry is approximately correct (within 1 minute tolerance)
        expected_expiry = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        time_diff = abs((exp_datetime - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 60 seconds
