"""
E2E Test: Event Management Flow
Tests complete event lifecycle from creation to booking
"""

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@pytest.mark.e2e
class TestEventManagementFlow:
    """Test event creation, browsing, and booking workflows"""

    def test_user_can_create_event(
        self, browser, base_url, api_client, user_factory, event_factory
    ):
        """Test that an authenticated user can create an event"""
        user_data = user_factory()
        event_data = event_factory()

        # Setup: Create and login user
        api_client.post("/api/v1/auth/register", json=user_data)
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )
        token = login_response.json()["access_token"]

        # Navigate to create event page
        browser.get(f"{base_url}/events/create")
        browser.add_cookie({"name": "access_token", "value": token})
        browser.refresh()

        wait = WebDriverWait(browser, 10)

        # Fill event creation form
        title_input = wait.until(
            EC.presence_of_element_located((By.ID, "event-title"))
        )
        title_input.send_keys(event_data["title"])

        description_input = wait.until(
            EC.presence_of_element_located((By.ID, "event-description"))
        )
        description_input.send_keys(event_data["description"])

        location_input = wait.until(
            EC.presence_of_element_located((By.ID, "event-location"))
        )
        location_input.send_keys(event_data["location"])

        max_attendees_input = wait.until(
            EC.presence_of_element_located((By.ID, "max-attendees"))
        )
        max_attendees_input.send_keys(str(event_data["max_attendees"]))

        # Submit form
        submit_button = wait.until(
            EC.element_to_be_clickable((By.ID, "create-event-submit"))
        )
        submit_button.click()

        # Wait for success message
        success_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )

        assert "created" in success_message.text.lower()

    def test_user_can_browse_public_events(self, browser, base_url, api_client):
        """Test that users can browse public events"""
        browser.get(f"{base_url}/events")

        wait = WebDriverWait(browser, 10)

        # Wait for events list to load
        events_container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "events-list"))
        )

        assert events_container.is_displayed()

    def test_user_can_view_event_details(
        self, browser, base_url, api_client, user_factory, event_factory, auth_headers
    ):
        """Test that users can view detailed event information"""
        user_data = user_factory()
        event_data = event_factory()

        # Setup: Create user and event via API
        api_client.post("/api/v1/auth/register", json=user_data)
        login_response = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=headers
        )
        event_id = event_response.json()["id"]

        # Navigate to event details page
        browser.get(f"{base_url}/events/{event_id}")

        wait = WebDriverWait(browser, 10)

        # Verify event details are displayed
        event_title = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "event-title"))
        )

        assert event_data["title"] in event_title.text

    def test_user_can_book_event(
        self, browser, base_url, api_client, user_factory, event_factory
    ):
        """Test that an authenticated user can book an event"""
        user_data = user_factory()
        event_data = event_factory()

        # Setup: Create user and event
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

        # Create another user to own the event
        organizer_data = user_factory()
        api_client.post("/api/v1/auth/register", json=organizer_data)
        organizer_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": organizer_data["email"],
                "password": organizer_data["password"],
            },
        )
        organizer_headers = {
            "Authorization": f"Bearer {organizer_login.json()['access_token']}"
        }

        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        # Navigate to event page and book
        browser.get(f"{base_url}/events/{event_id}")
        browser.add_cookie({"name": "access_token", "value": token})
        browser.refresh()

        wait = WebDriverWait(browser, 10)

        # Click book button
        book_button = wait.until(
            EC.element_to_be_clickable((By.ID, "book-event-button"))
        )
        book_button.click()

        # Wait for booking confirmation
        confirmation_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "booking-confirmation"))
        )

        assert "booked" in confirmation_message.text.lower()

    def test_user_can_search_events(self, browser, base_url):
        """Test that users can search for events"""
        browser.get(f"{base_url}/events")

        wait = WebDriverWait(browser, 10)

        # Find search input
        search_input = wait.until(
            EC.presence_of_element_located((By.ID, "event-search"))
        )
        search_input.send_keys("test event")

        # Click search button
        search_button = wait.until(
            EC.element_to_be_clickable((By.ID, "search-submit"))
        )
        search_button.click()

        # Wait for search results
        results_container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "search-results"))
        )

        assert results_container.is_displayed()

    def test_event_capacity_limits_bookings(
        self, browser, base_url, api_client, user_factory, event_factory
    ):
        """Test that events cannot be overbooked"""
        event_data = event_factory(max_attendees=1)
        organizer_data = user_factory()

        # Create organizer and event
        api_client.post("/api/v1/auth/register", json=organizer_data)
        organizer_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": organizer_data["email"],
                "password": organizer_data["password"],
            },
        )
        organizer_headers = {
            "Authorization": f"Bearer {organizer_login.json()['access_token']}"
        }

        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        # Create first user and book event
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
        api_client.post(f"/api/v1/events/{event_id}/book", headers=user1_headers)

        # Try to book with second user
        user2_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user2_data)
        user2_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user2_data["email"],
                "password": user2_data["password"],
            },
        )
        token = user2_login.json()["access_token"]

        browser.get(f"{base_url}/events/{event_id}")
        browser.add_cookie({"name": "access_token", "value": token})
        browser.refresh()

        wait = WebDriverWait(browser, 10)

        # Verify event is full
        full_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "event-full"))
        )

        assert "full" in full_message.text.lower() or "sold out" in full_message.text.lower()
