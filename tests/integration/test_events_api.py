"""
Integration Test: Events API
Tests all event-related API endpoints
"""

import pytest
from fastapi import status


@pytest.mark.integration
class TestEventsAPI:
    """Test events API endpoints"""

    def test_create_event_authenticated_success(
        self, api_client, auth_headers, event_factory
    ):
        """Test creating an event with valid authentication"""
        event_data = event_factory()

        response = api_client.post(
            "/api/v1/events", json=event_data, headers=auth_headers
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        data = response.json()
        assert data["title"] == event_data["title"]
        assert data["description"] == event_data["description"]
        assert "id" in data

    def test_create_event_unauthenticated_fails(self, api_client, event_factory):
        """Test that creating event without authentication fails"""
        event_data = event_factory()

        response = api_client.post("/api/v1/events", json=event_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_event_invalid_data_fails(self, api_client, auth_headers):
        """Test that creating event with invalid data fails"""
        invalid_data = {"title": ""}  # Missing required fields

        response = api_client.post(
            "/api/v1/events", json=invalid_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_events_success(self, api_client):
        """Test listing all public events"""
        response = api_client.get("/api/v1/events")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_list_events_with_pagination(self, api_client):
        """Test listing events with pagination"""
        response = api_client.get("/api/v1/events?skip=0&limit=10")

        assert response.status_code == status.HTTP_200_OK

    def test_get_event_by_id_success(
        self, api_client, auth_headers, event_factory
    ):
        """Test getting a specific event by ID"""
        event_data = event_factory()

        # Create event
        create_response = api_client.post(
            "/api/v1/events", json=event_data, headers=auth_headers
        )
        event_id = create_response.json()["id"]

        # Get event
        response = api_client.get(f"/api/v1/events/{event_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == event_id
        assert data["title"] == event_data["title"]

    def test_get_nonexistent_event_fails(self, api_client):
        """Test that getting non-existent event returns 404"""
        response = api_client.get("/api/v1/events/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_event_by_owner_success(
        self, api_client, auth_headers, event_factory
    ):
        """Test updating event by its owner"""
        event_data = event_factory()

        # Create event
        create_response = api_client.post(
            "/api/v1/events", json=event_data, headers=auth_headers
        )
        event_id = create_response.json()["id"]

        # Update event
        updated_data = {"title": "Updated Event Title"}
        response = api_client.put(
            f"/api/v1/events/{event_id}",
            json=updated_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == updated_data["title"]

    def test_update_event_by_non_owner_fails(
        self, api_client, user_factory, event_factory
    ):
        """Test that updating event by non-owner fails"""
        # Create first user and event
        user1_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user1_data)
        login1 = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user1_data["email"],
                "password": user1_data["password"],
            },
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        event_data = event_factory()
        create_response = api_client.post(
            "/api/v1/events", json=event_data, headers=headers1
        )
        event_id = create_response.json()["id"]

        # Create second user
        user2_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user2_data)
        login2 = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user2_data["email"],
                "password": user2_data["password"],
            },
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # Try to update with different user
        response = api_client.put(
            f"/api/v1/events/{event_id}",
            json={"title": "Hacked Title"},
            headers=headers2,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_event_by_owner_success(
        self, api_client, auth_headers, event_factory
    ):
        """Test deleting event by its owner"""
        event_data = event_factory()

        # Create event
        create_response = api_client.post(
            "/api/v1/events", json=event_data, headers=auth_headers
        )
        event_id = create_response.json()["id"]

        # Delete event
        response = api_client.delete(
            f"/api/v1/events/{event_id}", headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]

        # Verify deletion
        get_response = api_client.get(f"/api/v1/events/{event_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_events_by_title(self, api_client, auth_headers, event_factory):
        """Test searching events by title"""
        event_data = event_factory(title="Python Workshop 2025")

        # Create event
        api_client.post("/api/v1/events", json=event_data, headers=auth_headers)

        # Search
        response = api_client.get("/api/v1/events/search?q=Python")

        assert response.status_code == status.HTTP_200_OK

    def test_filter_events_by_date(self, api_client):
        """Test filtering events by date range"""
        response = api_client.get(
            "/api/v1/events?start_date=2025-01-01&end_date=2025-12-31"
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_user_created_events(self, api_client, auth_headers, event_factory):
        """Test getting events created by current user"""
        # Create multiple events
        for _ in range(3):
            event_data = event_factory()
            api_client.post("/api/v1/events", json=event_data, headers=auth_headers)

        # Get user's events
        response = api_client.get("/api/v1/events/my-events", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_event_visibility_public_vs_private(
        self, api_client, auth_headers, event_factory, user_factory
    ):
        """Test that private events are not visible to other users"""
        # Create private event
        private_event = event_factory(is_public=False)
        create_response = api_client.post(
            "/api/v1/events", json=private_event, headers=auth_headers
        )
        event_id = create_response.json()["id"]

        # Try to access as different user
        user2_data = user_factory()
        api_client.post("/api/v1/auth/register", json=user2_data)
        login2 = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": user2_data["email"],
                "password": user2_data["password"],
            },
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        response = api_client.get(f"/api/v1/events/{event_id}", headers=headers2)

        # Should be forbidden or not found
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
