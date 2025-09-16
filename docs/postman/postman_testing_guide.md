# Postman Testing Guide for Evently API

This guide provides detailed instructions and JSON examples to test every endpoint of the Evently API using Postman.

## 1. Setup Postman

### 1.1. Import the Collection and Environment

1.  **Import Collection**: Import the `evently.postman_collection.json` file into Postman. This will give you all the API requests.
2.  **Import Environment**: Import the `evently.postman_environment.json` file. This contains the `base_url` and `api_prefix` variables.

### 1.2. Configure Environment Variables

In the imported `evently` environment, make sure the following variables are set:

*   `base_url`: The base URL of your running application (e.g., `http://127.0.0.1:8000`).
*   `api_prefix`: The API prefix (e.g., `/api/v1`).
*   `access_token`: This will be automatically populated after you log in.
*   `admin_access_token`: You will need to manually set this after logging in with an admin account.

## 2. Authentication

### 2.1. Register a New User

*   **Request**: `(POST) {{base_url}}{{api_prefix}}/auth/register`
*   **Description**: Creates a new user account.

**Request Body:**

```json
{
  "email": "test.user@example.com",
  "password": "aVeryComplexPassword123!",
  "full_name": "Test User"
}
```

### 2.2. Login

*   **Request**: `(POST) {{base_url}}{{api_prefix}}/auth/login/access-token`
*   **Description**: Authenticates a user and returns an access token.

**Request Body (form-data):**

*   `username`: The user's email (`test.user@example.com`).
*   `password`: The user's password (`aVeryComplexPassword123!`).

After a successful login, the `access_token` environment variable will be updated.

### 2.3. Register and Login as an Admin

To test admin-only endpoints, you need an admin user.

1.  **Register Admin**: Use the "Register" endpoint with a new email and set `"is_superuser": true` in the request body. *Note: You might need to adjust the API to allow this or create an admin user directly in the database for testing.*

    **Request Body (Admin Registration):**

    ```json
    {
      "email": "admin@example.com",
      "password": "aVeryComplexPassword123!",
      "full_name": "Admin User",
      "is_superuser": true
    }
    ```

2.  **Login as Admin**: Use the "Login" endpoint with the admin credentials.
3.  **Save Admin Token**: After logging in as an admin, copy the `access_token` from the response and set it as the `admin_access_token` environment variable in Postman.

## 3. API Endpoints

---

### Events

#### 3.1.1. Get All Events

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/events/`
*   **Role**: Any

#### 3.1.2. Create an Event

*   **Request**: `(POST) {{base_url}}{{api_prefix}}/events/`
*   **Role**: Admin
*   **Authentication**: Use the `admin_access_token`.

**Request Body:**

```json
{
  "name": "New Tech Conference",
  "description": "A conference about the latest in tech.",
  "start_date": "2025-12-01T10:00:00Z",
  "end_date": "2025-12-03T18:00:00Z",
  "location": "Online",
  "price": 100.00,
  "capacity": 500
}
```

#### 3.1.3. Get a Specific Event

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/events/{event_id}`
*   **Role**: Any

#### 3.1.4. Update an Event

*   **Request**: `(PUT) {{base_url}}{{api_prefix}}/events/{event_id}`
*   **Role**: Admin
*   **Authentication**: Use the `admin_access_token`.

**Request Body:**

```json
{
  "name": "Updated Tech Conference",
  "price": 120.50
}
```

#### 3.1.5. Delete an Event

*   **Request**: `(DELETE) {{base_url}}{{api_prefix}}/events/{event_id}`
*   **Role**: Admin
*   **Authentication**: Use the `admin_access_token`.

---

### Bookings

#### 3.2.1. Create a Booking

*   **Request**: `(POST) {{base_url}}{{api_prefix}}/bookings/`
*   **Role**: User
*   **Authentication**: Use the `access_token`.

**Request Body:**

```json
{
  "event_id": 1,
  "number_of_tickets": 2
}
```

#### 3.2.2. Get All Bookings for a User

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/bookings/`
*   **Role**: User
*   **Authentication**: Use the `access_token`.

#### 3.2.3. Get a Specific Booking

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/bookings/{booking_id}`
*   **Role**: User (must own the booking) or Admin
*   **Authentication**: `access_token` or `admin_access_token`.

#### 3.2.4. Cancel a Booking

*   **Request**: `(PUT) {{base_url}}{{api_prefix}}/bookings/{booking_id}/cancel`
*   **Role**: User (must own the booking) or Admin
*   **Authentication**: `access_token` or `admin_access_token`.

---

### Users

#### 3.3.1. Get All Users

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/users/`
*   **Role**: Admin
*   **Authentication**: Use the `admin_access_token`.

#### 3.3.2. Get a Specific User

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/users/{user_id}`
*   **Role**: Admin
*   **Authentication**: Use the `admin_access_token`.

---

### Waitlist

#### 3.4.1. Join a Waitlist

*   **Request**: `(POST) {{base_url}}{{api_prefix}}/waitlist/{event_id}/join`
*   **Role**: User
*   **Authentication**: Use the `access_token`.

**Request Body:**

```json
{
  "number_of_tickets": 1
}
```

#### 3.4.2. Leave a Waitlist

*   **Request**: `(DELETE) {{base_url}}{{api_prefix}}/waitlist/{waitlist_id}`
*   **Role**: User (must be on the waitlist)
*   **Authentication**: Use the `access_token`.

---

### Analytics (Admin Only)

*Authentication for all analytics endpoints requires an `admin_access_token`.*

#### 3.5.1. Get Dashboard Stats

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/analytics/dashboard`

#### 3.5.2. Get Popular Events

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/analytics/popular-events`

#### 3.5.3. Get Event Performance

*   **Request**: `(GET) {{base_url}}{{api_prefix}}/analytics/event-performance/{event_id}`
