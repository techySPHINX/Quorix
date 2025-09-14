Analytics Endpoint

Base URL: {{base_url}}{{api_prefix}}/analytics

Authentication: Admin bearer token required for all analytics endpoints

Environment variables to set in Postman:

- base_url: http://localhost:8000
- api_prefix: /api/v1
- access_token: <admin_jwt_token>

Common Headers:

- Authorization: Bearer {{access_token}}

Key endpoints:

- GET /dashboard -> {{base_url}}{{api_prefix}}/analytics/dashboard
- GET /statistics?period_days=30 -> {{base_url}}{{api_prefix}}/analytics/statistics?period_days=30
- GET /popular-events?limit=10&period_days=30 -> {{base_url}}{{api_prefix}}/analytics/popular-events
- GET /trends?period=daily&days=30 -> {{base_url}}{{api_prefix}}/analytics/trends
- GET /revenue-analysis?period_days=30 -> {{base_url}}{{api_prefix}}/analytics/revenue-analysis
- GET /capacity-utilization -> {{base_url}}{{api_prefix}}/analytics/capacity-utilization
- GET /user-behavior?period_days=30 -> {{base_url}}{{api_prefix}}/analytics/user-behavior
- GET /cohort-analysis?months=6 -> {{base_url}}{{api_prefix}}/analytics/cohort-analysis
- GET /waitlist-analytics?period_days=30 -> {{base_url}}{{api_prefix}}/analytics/waitlist-analytics
- GET /event-performance/{event_id} -> {{base_url}}{{api_prefix}}/analytics/event-performance/{event_id}
- GET /geographical-analysis?period_days=30 -> {{base_url}}{{api_prefix}}/analytics/geographical-analysis
- GET /forecasting?forecast_days=30 -> {{base_url}}{{api_prefix}}/analytics/forecasting
- GET /real-time-metrics -> {{base_url}}{{api_prefix}}/analytics/real-time-metrics

Notes:

- These endpoints return aggregated metrics; ensure the database has seed data for meaningful outputs.
- Admin token is required (use `deps.require_role(UserRole.ADMIN)` in production).
