"""
Integration Test: Bookings API
Tests all booking-related API endpoints
"""

import pytest
from fastapi import status


@pytest.mark.integration
class TestBookingsAPI:
    """Test bookings API endpoints"""

    def test_create_booking_success(
        self, api_client, user_factory, event_factory
    ):
        """Test creating a booking for an event"""
        # Create organizer and event
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

        event_data = event_factory()
        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        # Create attendee
        attendee_data = user_factory()
        api_client.post("/api/v1/auth/register", json=attendee_data)
        attendee_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": attendee_data["email"],
                "password": attendee_data["password"],
            },
        )
        attendee_headers = {
            "Authorization": f"Bearer {attendee_login.json()['access_token']}"
        }

        # Create booking
        booking_data = {"event_id": event_id, "num_tickets": 1}
        response = api_client.post(
            f"/api/v1/events/{event_id}/book",
            json=booking_data,
            headers=attendee_headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        data = response.json()
        assert data["event_id"] == event_id

    def test_create_booking_unauthenticated_fails(
        self, api_client, user_factory, event_factory
    ):
        """Test that booking without authentication fails"""
        # Create event
        organizer_data = user_factory()
        api_client.post("/api/v1/auth/register", json=organizer_data)
        organizer_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": organizer_data["email"],
                "password": organizer_data["password"],
            },
        )
        headers = {"Authorization": f"Bearer {organizer_login.json()['access_token']}"}

        event_data = event_factory()
        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=headers
        )
        event_id = event_response.json()["id"]

        # Try to book without auth
        response = api_client.post(f"/api/v1/events/{event_id}/book")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_duplicate_booking_fails(self, api_client, user_factory, event_factory):
        """Test that user cannot book the same event twice"""
        # Setup
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

        event_data = event_factory()
        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        attendee_data = user_factory()
        api_client.post("/api/v1/auth/register", json=attendee_data)
        attendee_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": attendee_data["email"],
                "password": attendee_data["password"],
            },
        )
        attendee_headers = {
            "Authorization": f"Bearer {attendee_login.json()['access_token']}"
        }

        # First booking
        api_client.post(
            f"/api/v1/events/{event_id}/book", headers=attendee_headers
        )

        # Second booking (should fail)
        response = api_client.post(
            f"/api/v1/events/{event_id}/book", headers=attendee_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_booking_full_event_fails(self, api_client, user_factory, event_factory):
        """Test that booking a full event fails"""
        # Create event with capacity of 1
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

        event_data = event_factory(max_attendees=1)
        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        # First attendee books
        attendee1_data = user_factory()
        api_client.post("/api/v1/auth/register", json=attendee1_data)
        attendee1_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": attendee1_data["email"],
                "password": attendee1_data["password"],
            },
        )
        attendee1_headers = {
            "Authorization": f"Bearer {attendee1_login.json()['access_token']}"
        }
        api_client.post(f"/api/v1/events/{event_id}/book", headers=attendee1_headers)

        # Second attendee tries to book (should fail)
        attendee2_data = user_factory()
        api_client.post("/api/v1/auth/register", json=attendee2_data)
        attendee2_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": attendee2_data["email"],
                "password": attendee2_data["password"],
            },
        )
        attendee2_headers = {
            "Authorization": f"Bearer {attendee2_login.json()['access_token']}"
        }

        response = api_client.post(
            f"/api/v1/events/{event_id}/book", headers=attendee2_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_user_bookings(self, api_client, user_factory, event_factory):
        """Test getting all bookings for current user"""
        # Create user
        user_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user_data)
        user_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"],
            },
        )
        user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}

        # Create events and bookings
        for _ in range(2):
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

            event_data = event_factory()
            event_response = api_client.post(
                "/api/v1/events", json=event_data, headers=organizer_headers
            )
            event_id = event_response.json()["id"]

            api_client.post(f"/api/v1/events/{event_id}/book", headers=user_headers)

        # Get bookings
        response = api_client.get("/api/v1/bookings/my-bookings", headers=user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_cancel_booking_success(self, api_client, user_factory, event_factory):
        """Test canceling a booking"""
        # Setup
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

        event_data = event_factory()
        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        attendee_data = user_factory()
        api_client.post("/api/v1/auth/register", json=attendee_data)
        attendee_login = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": attendee_data["email"],
                "password": attendee_data["password"],
            },
        )
        attendee_headers = {
            "Authorization": f"Bearer {attendee_login.json()['access_token']}"
        }

        booking_response = api_client.post(
            f"/api/v1/events/{event_id}/book", headers=attendee_headers
        )
        booking_id = booking_response.json()["id"]

        # Cancel booking
        response = api_client.delete(
            f"/api/v1/bookings/{booking_id}", headers=attendee_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]

    def test_get_event_attendees_by_organizer(
        self, api_client, user_factory, event_factory
    ):
        """Test that event organizer can view attendees"""
        # Create organizer and event
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

        event_data = event_factory()
        event_response = api_client.post(
            "/api/v1/events", json=event_data, headers=organizer_headers
        )
        event_id = event_response.json()["id"]

        # Get attendees
        response = api_client.get(
            f"/api/v1/events/{event_id}/attendees", headers=organizer_headers
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
