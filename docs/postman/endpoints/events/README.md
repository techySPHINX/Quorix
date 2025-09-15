# Events Endpoint

Base URL:`{{base_url}}{{api_prefix}}/events`

Authentication: Bearer Token required for all endpoints except public listing (GET /)

Environment variables to set in Postman:

- base_url:`http://localhost:8000`
- api_prefix:`/api/v1`
- access_token:`<your_jwt_token>`

Common Headers:

- Content-Type: application/json
- Authorization: Bearer {{access_token}}

1. List events (GET)
   URL:`{{base_url}}{{api_prefix}}/events/`
   Method: GET
   Query parameters (optional): skip, limit, location, min_price, max_price, available_only
   Example:
   {{base_url}}{{api_prefix}}/events/?location=New%20York&max_price=100

Response: 200 OK - JSON array of events

2. Get event details (GET)
   URL:`{{base_url}}{{api_prefix}}/events/:event_id`
   Method: GET
   Path param: event_id (integer)

Example:
{{base_url}}{{api_prefix}}/events/123

Response: 200 OK - Event object

3. Create event (POST) - Admin only
   URL:`{{base_url}}{{api_prefix}}/events/`
   Method: POST
   Headers: Authorization: Bearer {{access_token}}
   Body (application/json):
   {
   "name": "Tech Conference 2024",
   "description": "Annual technology conference",
   "date": "2024-06-15T09:00:00Z",
   "location": "Convention Center",
   "max_attendees": 500,
   "price": 299.99,
   "category": "Technology"
   }

Response: 200 OK - created event

4. Update event (PUT) - Admin only
   URL:`{{base_url}}{{api_prefix}}/events/:event_id`
   Method: PUT
   Headers: Authorization: Bearer {{access_token}}
   Body: same as create

Response: 200 OK - updated event

5. Delete event (DELETE) - Admin only
   URL:`{{base_url}}{{api_prefix}}/events/:event_id`
   Method: DELETE
   Headers: Authorization: Bearer {{access_token}}

Response: 200 OK - deleted event object

Postman quick snippets (cURL)

Create event:
curl -X POST "{{base_url}}{{api_prefix}}/events/" \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer {{access_token}}" \
 -d '{
"name": "Tech Conference 2024",
"description": "Annual technology conference",
"date": "2024-06-15T09:00:00Z",
"location": "Convention Center",
"max_attendees": 500,
"price": 299.99,
"category": "Technology"
}'

Notes:

- Ensure the token belongs to an admin/superuser for create/update/delete.
- Date format must be ISO8601. Use Postman's pre-request scripts or a variable to insert dynamic dates.
