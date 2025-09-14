Notifications Endpoint

Base URL: {{base_url}}{{api_prefix}}/notifications

Authentication: Bearer Token required for user/admin endpoints

Environment variables to set in Postman:

- base_url: http://localhost:8000
- api_prefix: /api/v1
- access_token: <your_jwt_token>

Common Headers:

- Authorization: Bearer {{access_token}}

1. Get notifications (GET)
   URL: {{base_url}}{{api_prefix}}/notifications/
   Query params: skip, limit, unread_only, notification_types, priority
   Response: 200 OK - list of notifications

2. Get specific notification (GET)
   URL: {{base_url}}{{api_prefix}}/notifications/:notification_id
   Response: 200 OK - notification object

3. Mark notification read (PUT)
   URL: {{base_url}}{{api_prefix}}/notifications/:notification_id/mark-read
   Method: PUT
   Response: 200 OK - message + updated notification

4. Mark all read (PUT)
   URL: {{base_url}}{{api_prefix}}/notifications/mark-all-read
   Method: PUT
   Response: 200 OK - message

5. Delete notification (DELETE)
   URL: {{base_url}}{{api_prefix}}/notifications/:notification_id
   Method: DELETE
   Response: 200 OK - message

Admin-only endpoints:

- /notifications/admin/send-notification (POST)
- /notifications/admin/send-bulk (POST)
- /notifications/admin/create-bulk (POST)

Admin body params include user_id(s), notification_type, title, message, data (optional), priority, send_email

Notes:

- Notification types and priority are enums. Use integer or string values depending on API schema; check `app.models.notification` for exact enum names.
