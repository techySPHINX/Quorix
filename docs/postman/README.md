Evently Postman Testing Guide

This folder contains per-endpoint Postman-ready documentation to test the Evently API manually.

How to use:

1. Import `evently.postman_environment.json` into Postman as an environment. Set `base_url` and `access_token` as needed.
2. For each endpoint, open the corresponding folder under `endpoints/` and copy the example requests into new Postman requests.
3. Use the `{{base_url}}{{api_prefix}}/...` templates to avoid changing URLs across requests.

Tips:

- Use the `Auth -> Bearer Token` type in Postman and set the token to `{{access_token}}`.
- For endpoints triggering background tasks (emails, celery), run a local Celery worker or mock tasks.
- Some admin-only endpoints require an admin token. You can create a test admin user or set `is_superuser` in your fixture data.

Folders included:

- endpoints/events
- endpoints/bookings
- endpoints/auth
- endpoints/users
- endpoints/notifications
- endpoints/waitlist
- endpoints/analytics

If you'd like, I can also generate a Postman Collection JSON (v2.1) with all requests pre-populated. Let me know if you want that exported and committed.

Postman Collection (ready-to-import)

A full Postman Collection has been generated and committed as `evently.postman_collection.json` in this folder. It includes all endpoints, example request bodies, and example responses. To import into Postman:

1. In Postman, click Import -> File and select `docs/postman/evently.postman_collection.json`.
2. Import the environment `docs/postman/evently.postman_environment.json` (Import -> File) or create an environment and add these variables:
   - `base_url` (e.g., `http://localhost:8000`)
   - `api_prefix` (default `/api/v1`)
   - `access_token` (fill after login)
3. Run requests. For protected endpoints, set the Bearer token to `{{access_token}}` or use request-level Authorization.

Admin vs User variants

The collection contains requests primarily for the default user flow. For admin-only requests (create/update/delete events, admin notification endpoints, analytics), use an admin token in `{{access_token}}` or duplicate the requests and set an `{{admin_access_token}}` variable if you want both variations visible.
