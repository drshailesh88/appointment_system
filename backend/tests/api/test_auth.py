"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestAuth:
    """Authentication endpoint tests."""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@test.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, test_user, auth_headers):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name

    def test_get_current_user_no_token(self, client: TestClient):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
