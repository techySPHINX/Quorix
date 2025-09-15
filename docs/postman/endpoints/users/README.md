# Users Endpoint

Base URL:`{{base_url}}{{api_prefix}}/users`

Authentication: Bearer Token required for all endpoints (Admin for listing)

Environment variables to set in Postman:

- base_url:`http://localhost:8000`
- api_prefix:`/api/v1`
- access_token:`<your_jwt_token>`

Common Headers:

- Authorization: Bearer {{access_token}}

1. List users (GET) - Admin only
   URL:`{{base_url}}{{api_prefix}}/users/`
   Method: GET
   Query params: skip, limit
   Response: 200 OK - list of user objects

2. Get user by ID (GET)
   URL:`{{base_url}}{{api_prefix}}/users/:user_id`
   Method: GET
   Response: 200 OK - user object
   Errors:

- 404 if user not found
- 400 if requesting another user's details without admin rights

Notes:

- Ensure token used for listing belongs to an admin account.
