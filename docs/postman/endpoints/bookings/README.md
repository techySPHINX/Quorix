Bookings Endpoint

Base URL: {{base_url}}{{api_prefix}}/bookings

Authentication: Bearer Token required for all bookings endpoints

Environment variables to set in Postman:

- base_url: http://localhost:8000
- api_prefix: /api/v1
- access_token: <your_jwt_token>

Common Headers:

- Content-Type: application/json
- Authorization: Bearer {{access_token}}

1. Create booking (POST)
   URL: {{base_url}}{{api_prefix}}/bookings/
   Method: POST
   Body (application/json):
   {
   "event_id": 123,
   "number_of_tickets": 2,
   "attendee_info": [
   {"name": "Alice", "email": "alice@example.com"},
   {"name": "Bob", "email": "bob@example.com"}
   ]
   }

Response: 200 OK - booking object
Errors:

- 404 if event not found
- 400 with suggestion to join waitlist if not enough tickets

2. List bookings (GET)
   URL: {{base_url}}{{api_prefix}}/bookings/
   Method: GET
   Query params: skip, limit
   Returns: 200 OK - list of bookings (admin sees all, users see own)

3. Get booking by ID (GET)
   URL: {{base_url}}{{api_prefix}}/bookings/:booking_id
   Method: GET
   Returns: 200 OK - booking object

4. Cancel booking (PUT)
   URL: {{base_url}}{{api_prefix}}/bookings/:booking_id/cancel
   Method: PUT
   Headers: Authorization: Bearer {{access_token}}
   Returns: 200 OK - cancelled booking

Notes:

- Booking creation triggers background emails via Celery; in local testing you may need to run the worker or mock the task calls.
- If event is sold out, the response includes a suggestion to join the waitlist with the URL: /api/v1/waitlist/{event.id}/join
