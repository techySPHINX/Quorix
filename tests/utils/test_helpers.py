"""
Test Helper Utilities
Provides common utilities for tests
"""

import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict

from faker import Faker

fake = Faker()


def generate_random_string(length: int = 10) -> str:
    """Generate a random string"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_email() -> str:
    """Generate a random email address"""
    return fake.email()


def generate_future_datetime(days: int = 30) -> datetime:
    """Generate a future datetime"""
    return datetime.now() + timedelta(days=random.randint(1, days))


def generate_test_user_data(**overrides) -> Dict[str, Any]:
    """Generate test user data with optional overrides"""
    data = {
        "email": fake.email(),
        "username": fake.user_name(),
        "password": "TestPassword123!",
        "full_name": fake.name(),
        "is_active": True,
        "is_superuser": False,
    }
    data.update(overrides)
    return data


def generate_test_event_data(**overrides) -> Dict[str, Any]:
    """Generate test event data with optional overrides"""
    start_time = generate_future_datetime(30)
    end_time = start_time + timedelta(hours=2)

    data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.text(max_nb_chars=200),
        "location": fake.address(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "max_attendees": random.randint(10, 100),
        "is_public": True,
    }
    data.update(overrides)
    return data


def generate_test_booking_data(**overrides) -> Dict[str, Any]:
    """Generate test booking data with optional overrides"""
    data = {
        "num_tickets": 1,
        "status": "confirmed",
    }
    data.update(overrides)
    return data


class APITestHelper:
    """Helper class for API testing"""

    def __init__(self, client):
        self.client = client
        self.tokens = {}

    def register_user(self, user_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Register a new user and return response data"""
        if user_data is None:
            user_data = generate_test_user_data()

        response = self.client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code in [200, 201]
        return response.json()

    def login_user(self, email: str, password: str) -> str:
        """Login user and return access token"""
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        self.tokens[email] = token
        return token

    def get_auth_headers(self, email: str) -> Dict[str, str]:
        """Get authorization headers for user"""
        token = self.tokens.get(email)
        if not token:
            raise ValueError(f"No token found for user {email}")
        return {"Authorization": f"Bearer {token}"}

    def create_event(
        self, event_data: Dict[str, Any], token: str
    ) -> Dict[str, Any]:
        """Create an event and return response data"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/api/v1/events", json=event_data, headers=headers)
        assert response.status_code in [200, 201]
        return response.json()

    def book_event(
        self, event_id: int, token: str, num_tickets: int = 1
    ) -> Dict[str, Any]:
        """Book an event and return response data"""
        headers = {"Authorization": f"Bearer {token}"}
        booking_data = {"num_tickets": num_tickets}
        response = self.client.post(
            f"/api/v1/events/{event_id}/book",
            json=booking_data,
            headers=headers,
        )
        assert response.status_code in [200, 201]
        return response.json()


class SeleniumTestHelper:
    """Helper class for Selenium E2E testing"""

    def __init__(self, driver, base_url: str):
        self.driver = driver
        self.base_url = base_url

    def navigate_to(self, path: str):
        """Navigate to a specific path"""
        self.driver.get(f"{self.base_url}{path}")

    def fill_form_field(self, field_id: str, value: str):
        """Fill a form field by ID"""
        element = self.driver.find_element("id", field_id)
        element.clear()
        element.send_keys(value)

    def click_button(self, button_id: str):
        """Click a button by ID"""
        button = self.driver.find_element("id", button_id)
        button.click()

    def wait_for_element(self, locator, timeout: int = 10):
        """Wait for element to be present"""
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def get_current_url(self) -> str:
        """Get current URL"""
        return self.driver.current_url

    def set_auth_cookie(self, token: str):
        """Set authentication cookie"""
        self.driver.add_cookie({"name": "access_token", "value": token})
        self.driver.refresh()


def assert_response_success(response, expected_status_codes=(200, 201)):
    """Assert that API response is successful"""
    assert response.status_code in expected_status_codes, (
        f"Expected status code in {expected_status_codes}, "
        f"got {response.status_code}: {response.text}"
    )


def assert_response_error(response, expected_status_code: int):
    """Assert that API response has expected error"""
    assert response.status_code == expected_status_code, (
        f"Expected status code {expected_status_code}, "
        f"got {response.status_code}: {response.text}"
    )


def assert_valid_jwt_token(token: str):
    """Assert that token is a valid JWT format"""
    parts = token.split(".")
    assert len(parts) == 3, "JWT token must have 3 parts"
    for part in parts:
        assert part, "JWT token parts cannot be empty"
