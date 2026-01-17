"""
E2E Test: User Registration and Authentication Flow
Tests complete user journey from registration to login
"""

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

@pytest.mark.e2e
class TestUserRegistrationFlow:
    """Test user registration and authentication workflows"""

    def test_user_can_register_successfully(self, browser, base_url, user_factory):
        """Test that a new user can register successfully"""
        user_data = user_factory()

        # Navigate to registration page
        browser.get(f"{base_url}/register")

        # Wait for page to load
        wait = WebDriverWait(browser, 10)

        # Fill registration form
        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(user_data["email"])

        username_input = wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_input.send_keys(user_data["username"])

        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_input.send_keys(user_data["password"])

        full_name_input = wait.until(
            EC.presence_of_element_located((By.ID, "full_name"))
        )
        full_name_input.send_keys(user_data["full_name"])

        # Submit form
        submit_button = wait.until(
            EC.element_to_be_clickable((By.ID, "register-submit"))
        )
        submit_button.click()

        # Wait for success message or redirect
        success_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )

        assert "successfully" in success_message.text.lower()

    def test_user_can_login_with_valid_credentials(
        self, browser, base_url, api_client, user_factory
    ):
        """Test that a user can login with valid credentials"""
        user_data = user_factory()

        # Create user via API
        api_client.post("/api/v1/auth/register", json=user_data)

        # Navigate to login page
        browser.get(f"{base_url}/login")

        wait = WebDriverWait(browser, 10)

        # Fill login form
        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(user_data["email"])

        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_input.send_keys(user_data["password"])

        # Submit form
        login_button = wait.until(
            EC.element_to_be_clickable((By.ID, "login-submit"))
        )
        login_button.click()

        # Wait for redirect to dashboard
        wait.until(EC.url_contains("/dashboard"))

        assert "dashboard" in browser.current_url.lower()

    def test_user_cannot_login_with_invalid_credentials(
        self, browser, base_url, user_factory
    ):
        """Test that login fails with invalid credentials"""
        user_data = user_factory()

        browser.get(f"{base_url}/login")

        wait = WebDriverWait(browser, 10)

        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(user_data["email"])

        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_input.send_keys("WrongPassword123!")

        login_button = wait.until(
            EC.element_to_be_clickable((By.ID, "login-submit"))
        )
        login_button.click()

        # Wait for error message
        error_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
        )

        assert "invalid" in error_message.text.lower()

    def test_registration_validates_email_format(self, browser, base_url, user_factory):
        """Test that registration validates email format"""
        user_data = user_factory()
        user_data["email"] = "invalid-email"

        browser.get(f"{base_url}/register")

        wait = WebDriverWait(browser, 10)

        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(user_data["email"])

        username_input = wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_input.send_keys(user_data["username"])

        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_input.send_keys(user_data["password"])

        submit_button = wait.until(
            EC.element_to_be_clickable((By.ID, "register-submit"))
        )
        submit_button.click()

        # Check for validation error
        error_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "validation-error"))
        )

        assert "email" in error_message.text.lower()

    def test_user_can_logout(self, browser, base_url, api_client, user_factory):
        """Test that a logged-in user can logout"""
        user_data = user_factory()

        # Create and login user via API
        api_client.post("/api/v1/auth/register", json=user_data)
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )
        token = login_response.json()["access_token"]

        # Navigate to dashboard with token
        browser.get(f"{base_url}/dashboard")
        browser.add_cookie({"name": "access_token", "value": token})
        browser.refresh()

        wait = WebDriverWait(browser, 10)

        # Click logout button
        logout_button = wait.until(
            EC.element_to_be_clickable((By.ID, "logout-button"))
        )
        logout_button.click()

        # Verify redirect to login page
        wait.until(EC.url_contains("/login"))
        assert "login" in browser.current_url.lower()
