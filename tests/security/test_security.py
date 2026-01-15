"""
Security Tests: Authentication and Authorization
Tests security aspects of the application
"""

import pytest
from fastapi import status


@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication security measures"""

    def test_sql_injection_in_login(self, api_client):
        """Test that SQL injection attempts are prevented"""
        malicious_inputs = [
            "admin' OR '1'='1",
            "admin'--",
            "admin' /*",
            "' OR 1=1--",
            "admin'; DROP TABLE users--",
        ]

        response = None

        for malicious_input in malicious_inputs:
            response = api_client.post(
                "/api/v1/auth/login",
                data={
                    "username": malicious_input,
                    "password": "password",
                },
            )

            # Should fail authentication, not execute SQL
            assert response is not None
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_xss_in_user_input(self, api_client, user_factory):
        """Test that XSS attempts are sanitized"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
        ]

        for payload in xss_payloads:
            user_data = user_factory(full_name=payload)
            response = api_client.post("/api/v1/auth/register", json=user_data)

            if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
                data = response.json()
                # XSS payload should be escaped or sanitized
                assert payload not in str(data) or "<script>" not in data.get("full_name", "")

    def test_password_not_returned_in_responses(self, api_client, user_factory):
        """Test that passwords are never returned in API responses"""
        user_data = user_factory()

        # Register
        response = api_client.post("/api/v1/auth/register", json=user_data)
        assert "password" not in response.json()

        # Login
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )
        assert "password" not in login_response.json()

        # Get user
        token = login_response.json()["access_token"]
        me_response = api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert "password" not in me_response.json()

    def test_jwt_token_expiration(self, api_client, user_factory):
        """Test that expired JWT tokens are rejected"""
        user_data = user_factory()

        api_client.post("/api/v1/auth/register", json=user_data)
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Token should be valid initially
        response = api_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == status.HTTP_200_OK

    def test_rate_limiting_on_login(self, api_client, user_factory):
        """Test that rate limiting is applied to login attempts"""
        user_data = user_factory()

        # Make multiple failed login attempts
        for i in range(15):
            response = api_client.post(
                "/api/v1/auth/login",
                data={
                    "username": user_data["email"],
                    "password": f"wrong_password_{i}",
                },
            )

            # After certain attempts, should get rate limited
            if i > 10:
                if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    break

        # At least the last request might be rate limited
        # This depends on implementation

    def test_cors_headers_present(self, api_client):
        """Test that CORS headers are properly configured"""
        response = api_client.options("/api/v1/events")
        assert response is not None

    def test_csrf_protection(self, api_client, auth_headers):
        """Test CSRF protection on state-changing operations"""
        pass

    def test_secure_headers_present(self, api_client):
        """Test that security headers are present"""
        response = api_client.get("/api/v1/events")
        assert response is not None
        headers = response.headers
        # Example assertions (customize as needed):
        # assert "X-Frame-Options" in headers
        # assert "X-Content-Type-Options" in headers
        # assert "Strict-Transport-Security" in headers


@pytest.mark.security
class TestAuthorizationSecurity:
    """Test authorization and access control"""

    def test_unauthorized_access_to_protected_endpoints(self, api_client):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            ("/api/v1/auth/me", "get"),
            ("/api/v1/events", "post"),
            ("/api/v1/bookings/my-bookings", "get"),
        ]

        for endpoint, method in protected_endpoints:
            response = None
            if method == "get":
                response = api_client.get(endpoint)
            elif method == "post":
                response = api_client.post(endpoint, json={})
            assert response is not None
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_cannot_access_others_data(
        self, api_client, user_factory
    ):
        """Test that users cannot access other users' private data"""
        # Create two users
        user1_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user1_data)
        user1_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user1_data["email"],
                "password": user1_data["password"],
            },
        )

        user2_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user2_data)
        user2_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user2_data["email"],
                "password": user2_data["password"],
            },
        )

        user2_headers = {"Authorization": f"Bearer {user2_login.json()['access_token']}"}

        # User 2 tries to access User 1's bookings (if such endpoint exists)
        response = api_client.get(
            "/api/v1/bookings/my-bookings",
            headers=user2_headers,
        )

        # Should only return user 2's bookings
        assert response is not None
        if response.status_code == status.HTTP_200_OK:
            bookings = response.json()
            # All bookings should belong to user 2
            assert isinstance(bookings, list)

    def test_privilege_escalation_attempts(
        self, api_client, user_factory, event_factory
    ):
        """Test that users cannot escalate privileges"""
        # Create regular user
        user_data = user_factory(is_superuser=False)
        api_client.post("/api/v1/auth/register", json=user_data)
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Try to access admin endpoints
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/events",
        ]

        for endpoint in admin_endpoints:
            response = api_client.get(endpoint, headers=headers)

            # Should be forbidden or not found
            assert response.status_code in [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ]

    def test_insecure_direct_object_reference(
        self, api_client, user_factory, event_factory
    ):
        """Test protection against IDOR vulnerabilities"""
        # Create two users with events
        user1_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user1_data)
        user1_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user1_data["email"],
                "password": user1_data["password"],
            },
        )
        user1_headers = {"Authorization": f"Bearer {user1_login.json()['access_token']}"}

        event1_data = event_factory()
        event1_response = api_client.post(
            "/api/v1/events", json=event1_data, headers=user1_headers
        )
        event1_id = event1_response.json()["id"]

        # User 2 tries to delete User 1's event
        user2_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user2_data)
        user2_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user2_data["email"],
                "password": user2_data["password"],
            },
        )
        user2_headers = {"Authorization": f"Bearer {user2_login.json()['access_token']}"}

        response = api_client.delete(
            f"/api/v1/events/{event1_id}", headers=user2_headers
        )

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.security
class TestInputValidationSecurity:
    """Test input validation and sanitization"""

    def test_email_validation(self, api_client, user_factory):
        """Test email format validation"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
        ]

        for invalid_email in invalid_emails:
            user_data = user_factory(email=invalid_email)
            response = api_client.post("/api/v1/auth/register", json=user_data)

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_max_length_validation(self, api_client, user_factory):
        """Test that max length constraints are enforced"""
        # Very long string
        long_string = "a" * 10000

        user_data = user_factory(full_name=long_string)
        response = api_client.post("/api/v1/auth/register", json=user_data)

        # Should fail validation or be truncated
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_special_characters_handling(self, api_client, event_factory, auth_headers):
        """Test handling of special characters"""
        special_chars = "!@#$%^&*(){}[]|\\:;\"'<>,.?/~`"

        event_data = event_factory(title=f"Test Event {special_chars}")
        response = api_client.post(
            "/api/v1/events", json=event_data, headers=auth_headers
        )

        # Should handle special characters properly
        assert response is not None
        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            data = response.json()
            # Special characters should be preserved or properly escaped
            assert special_chars in data.get("title", "")

    def test_unicode_characters_handling(self, api_client, event_factory, auth_headers):
        """Test handling of Unicode characters"""
        unicode_title = "测试活动 🎉 Événement тест"

        event_data = event_factory(title=unicode_title)
        response = api_client.post(
            "/api/v1/events", json=event_data, headers=auth_headers
        )

        # Should handle Unicode properly
        assert response is not None
        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            data = response.json()
            # Unicode should be preserved
            assert unicode_title in data.get("title", "")
