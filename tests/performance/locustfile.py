"""
Performance Test Configuration
Uses Locust for load testing
"""

from locust import HttpUser, between, task

class EventlyUser(HttpUser):
    """Simulated user for performance testing"""

    wait_time = between(1, 3)

    def on_start(self):
        """Setup: Register and login"""
        # Register
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": f"test{self.environment.stats.num_requests}@example.com",
                "username": f"testuser{self.environment.stats.num_requests}",
                "password": "TestPassword123!",
                "full_name": "Test User",
            },
        )

        # Login
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": f"test{self.environment.stats.num_requests}@example.com",
                "password": "TestPassword123!",
            },
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def list_events(self):
        """Task: List all events"""
        self.client.get("/api/v1/events")

    @task(2)
    def view_event_details(self):
        """Task: View specific event details"""
        # Assume event ID 1 exists
        self.client.get("/api/v1/events/1")

    @task(1)
    def create_event(self):
        """Task: Create a new event"""
        if self.token:
            self.client.post(
                "/api/v1/events",
                json={
                    "title": "Performance Test Event",
                    "description": "Event created during load testing",
                    "location": "Test Location",
                    "start_time": "2025-12-31T10:00:00",
                    "end_time": "2025-12-31T12:00:00",
                    "max_attendees": 100,
                    "is_public": True,
                },
                headers=self.headers,
            )

    @task(2)
    def search_events(self):
        """Task: Search for events"""
        self.client.get("/api/v1/events/search?q=test")

    @task(1)
    def get_my_bookings(self):
        """Task: Get user's bookings"""
        if self.token:
            self.client.get("/api/v1/bookings/my-bookings", headers=self.headers)

    @task(1)
    def book_event(self):
        """Task: Book an event"""
        if self.token:
            # Assume event ID 1 exists
            self.client.post(
                "/api/v1/events/1/book",
                headers=self.headers,
            )


class AdminUser(HttpUser):
    """Simulated admin user for performance testing"""

    wait_time = between(2, 5)

    def on_start(self):
        """Setup: Admin login"""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task
    def view_all_users(self):
        """Task: View all users (admin)"""
        if self.token:
            self.client.get("/api/v1/admin/users", headers=self.headers)

    @task
    def view_analytics(self):
        """Task: View analytics (admin)"""
        if self.token:
            self.client.get("/api/v1/admin/analytics", headers=self.headers)
