# Auth Endpoint

Base URL:`{{base_url}}{{api_prefix}}/auth`

Environment variables to set in Postman:

- base_url:`http://localhost:8000`
- api_prefix:`/api/v1`

Common Headers:

- For token requests: Content-Type: application/x-www-form-urlencoded
- For JSON refresh: Content-Type: application/json

1. Login (POST)
   URL:`{{base_url}}{{api_prefix}}/auth/login/access-token`
   Method: POST
   Body (x-www-form-urlencoded):

- username: user@example.com
- password: securepassword123
  Response: 200 OK - JSON with access_token, refresh_token, token_type

cURL example:
curl -X POST "{{base_url}}{{api_prefix}}/auth/login/access-token" \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "username=user@example.com&password=securepassword123"

2. Refresh token (POST)
   URL:`{{base_url}}{{api_prefix}}/auth/login/refresh-token`
   Method: POST
   Body (application/json): {"refresh_token": "<your_refresh_token>"}
   Response: 200 OK - new access_token

3. Test token (POST)
   URL:`{{base_url}}{{api_prefix}}/auth/login/test-token`
   Method: POST
   Headers: Authorization: Bearer {{access_token}}
   Response: 200 OK - user object

4. Logout (POST)
   URL:`{{base_url}}{{api_prefix}}/auth/logout`
   Method: POST
   Headers: Authorization: Bearer {{access_token}}
   Response: 200 OK - message

Notes:

- Tokens are stored in Redis. For local testing, ensure Redis is running or adjust `deps.get_redis_client` to provide a mock.
