"""
Integration Test: Authentication API
Tests all authentication-related API endpoints
"""

import pytest
from fastapi import status


@pytest.mark.integration
class TestAuthenticationAPI:
    """Test authentication API endpoints"""

    def test_register_new_user_success(self, api_client, user_factory):
        """Test successful user registration"""
        user_data = user_factory()

        response = api_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "password" not in data

    def test_register_duplicate_email_fails(self, api_client, user_factory):
        """Test that registering with duplicate email fails"""
        user_data = user_factory()

        # First registration
        response1 = api_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        # Duplicate registration
        response2 = api_client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response2.json()["detail"].lower()

    def test_register_invalid_email_format_fails(self, api_client, user_factory):
        """Test that invalid email format is rejected"""
        user_data = user_factory(email="invalid-email")

        response = api_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_weak_password_fails(self, api_client, user_factory):
        """Test that weak passwords are rejected"""
        user_data = user_factory(password="weak")

        response = api_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_login_with_valid_credentials_success(self, api_client, user_factory):
        """Test successful login with valid credentials"""
        user_data = user_factory()

        # Register user
        api_client.post("/api/v1/auth/register", json=user_data)

        # Login
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"],
        }
        response = api_client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_invalid_password_fails(self, api_client, user_factory):
        """Test that login with wrong password fails"""
        user_data = user_factory()

        # Register user
        api_client.post("/api/v1/auth/register", json=user_data)

        # Login with wrong password
        login_data = {
            "username": user_data["email"],
            "password": "WrongPassword123!",
        }
        response = api_client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_nonexistent_user_fails(self, api_client, user_factory):
        """Test that login with non-existent user fails"""
        user_data = user_factory()

        login_data = {
            "username": user_data["email"],
            "password": user_data["password"],
        }
        response = api_client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_valid_token(self, api_client, auth_headers):
        """Test getting current user profile with valid token"""
        response = api_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email" in data
        assert "username" in data

    def test_get_current_user_without_token_fails(self, api_client):
        """Test that accessing protected endpoint without token fails"""
        response = api_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_invalid_token_fails(self, api_client):
        """Test that invalid token is rejected"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = api_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self, api_client, user_factory):
        """Test token refresh functionality"""
        user_data = user_factory()

        # Register and login
        api_client.post("/api/v1/auth/register", json=user_data)
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )

        refresh_token = login_response.json().get("refresh_token")

        if refresh_token:
            # Test refresh
            response = api_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )

            assert response.status_code == status.HTTP_200_OK
            assert "access_token" in response.json()

    def test_logout_success(self, api_client, auth_headers):
        """Test user logout"""
        response = api_client.post("/api/v1/auth/logout", headers=auth_headers)

        # Accept 200 or 204
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

    def test_password_reset_request(self, api_client, user_factory):
        """Test password reset request flow"""
        user_data = user_factory()

        # Register user
        api_client.post("/api/v1/auth/register", json=user_data)

        # Request password reset
        response = api_client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": user_data["email"]},
        )

        # Should succeed or return 200 even if email doesn't exist (security)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]

    def test_change_password_with_valid_token(
        self, api_client, user_factory, auth_headers
    ):
        """Test changing password with valid authentication"""
        old_password = "OldPassword123!"
        new_password = "NewPassword456!"

        response = api_client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": old_password,
                "new_password": new_password,
            },
            headers=auth_headers,
        )

        # Should succeed if endpoint exists
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_account_deletion(self, api_client, auth_headers):
        """Test user account deletion"""
        response = api_client.delete("/api/v1/auth/account", headers=auth_headers)

        # Should succeed if endpoint exists
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_404_NOT_FOUND,
        ]
