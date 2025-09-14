Waitlist Endpoint

Base URL: {{base_url}}{{api_prefix}}/waitlist

Authentication: Bearer Token required

Environment variables to set in Postman:

- base_url: http://localhost:8000
- api_prefix: /api/v1
- access_token: <your_jwt_token>

Common Headers:

- Authorization: Bearer {{access_token}}

1. Join waitlist (POST)
   URL: {{base_url}}{{api_prefix}}/waitlist/:event_id/join
   Method: POST
   Body (application/json):
   {
   "number_of_tickets": 2,
   "contact_info": {"name": "Alice", "email": "alice@example.com"}
   }
   Response: 200 OK - waitlist entry

2. Get my waitlist (GET)
   URL: {{base_url}}{{api_prefix}}/waitlist/my-waitlist
   Method: GET
   Response: 200 OK - list of waitlist entries for current user

3. Leave waitlist (DELETE)
   URL: {{base_url}}{{api_prefix}}/waitlist/:waitlist_id
   Method: DELETE
   Response: 200 OK - message

4. Event waitlist stats (GET) - Admin only
   URL: {{base_url}}{{api_prefix}}/waitlist/:event_id/stats
   Method: GET
   Response: 200 OK - stats

5. Get event waitlist (GET) - Admin only
   URL: {{base_url}}{{api_prefix}}/waitlist/:event_id/list
   Method: GET
   Response: 200 OK - list of waitlist entries

Notes:

- Admin endpoints require the token with admin privileges.
