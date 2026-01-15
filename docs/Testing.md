# Evently Automation Testing Framework

## Overview

This comprehensive testing framework provides production-grade test coverage for the Evently platform, including:

- **E2E Tests (Selenium)**: Browser automation tests
- **Integration Tests**: API endpoint tests
- **Unit Tests**: Component-level tests
- **Security Tests**: Authentication, authorization, and vulnerability tests
- **Performance Tests**: Load testing with Locust

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── e2e/                     # End-to-end browser tests
│   ├── test_user_registration_flow.py
│   └── test_event_management_flow.py
├── integration/             # API integration tests
│   ├── test_auth_api.py
│   ├── test_events_api.py
│   └── test_bookings_api.py
├── security/                # Security tests
│   └── test_security.py
├── performance/             # Performance tests
│   └── locustfile.py
└── utils/                   # Test utilities
    └── test_helpers.py
```

## Prerequisites

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Browser Drivers (for E2E tests)

The framework automatically downloads and manages browser drivers using `webdriver-manager`. Supported browsers:

- Chrome (default)
- Firefox

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# Security tests
pytest -m security

# Performance tests (not in default suite)
pytest -m performance
```

### Run Tests by Module

```bash
# Authentication tests
pytest tests/integration/test_auth_api.py

# Event management tests
pytest tests/integration/test_events_api.py

# E2E user flow
pytest tests/e2e/test_user_registration_flow.py
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest -n auto
```

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html

# View HTML coverage report
# Open htmlcov/index.html in browser
```

### Run with Specific Browser

```bash
# Chrome (default)
pytest tests/e2e/ --browser=chrome

# Firefox
pytest tests/e2e/ --browser=firefox
```

## E2E Testing

### Prerequisites

1. Start the application:

```bash
uvicorn app.main:app --reload
```

2. Ensure database and Redis are running:

```bash
docker-compose up -d postgres redis
```

### Run E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run with visible browser (not headless)
pytest tests/e2e/ --headed

# Run specific E2E test
pytest tests/e2e/test_user_registration_flow.py::TestUserRegistrationFlow::test_user_can_register_successfully
```

## Integration Testing

Integration tests verify API endpoints with database interactions.

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run authentication tests
pytest tests/integration/test_auth_api.py -v

# Run event API tests
pytest tests/integration/test_events_api.py -v
```

## Security Testing

Security tests verify protection against common vulnerabilities:

- SQL Injection
- XSS (Cross-Site Scripting)
- CSRF (Cross-Site Request Forgery)
- Authentication bypass
- Authorization bypass
- Input validation

```bash
# Run all security tests
pytest tests/security/ -v -m security

# Run specific security test
pytest tests/security/test_security.py::TestAuthenticationSecurity::test_sql_injection_in_login
```

## Performance Testing

### Using Locust

Locust provides load testing capabilities.

```bash
# Start Locust web UI
locust -f tests/performance/locustfile.py

# Open browser to http://localhost:8089
# Configure number of users and spawn rate
```

### Locust CLI (Headless)

```bash
# Run load test with 100 users
locust -f tests/performance/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host http://localhost:8000

# Generate HTML report
locust -f tests/performance/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host http://localhost:8000 \
  --html report.html
```

## Test Fixtures

### Available Fixtures

- `api_client`: FastAPI TestClient with database override
- `async_api_client`: Async HTTP client
- `browser`: Selenium WebDriver instance
- `auth_token`: JWT token for authenticated requests
- `auth_headers`: Authorization headers
- `user_factory`: Factory for creating test users
- `event_factory`: Factory for creating test events
- `booking_factory`: Factory for creating test bookings
- `mock_redis`: Mocked Redis client
- `mock_celery_task`: Mocked Celery task

### Example Usage

```python
import pytest

@pytest.mark.integration
def test_create_event(api_client, auth_headers, event_factory):
    """Test creating an event"""
    event_data = event_factory()
    response = api_client.post(
        "/api/v1/events",
        json=event_data,
        headers=auth_headers
    )
    assert response.status_code == 201
```

## CI/CD Integration

Tests are automatically run in the CI/CD pipeline on:

- Pull requests
- Pushes to main/develop branches

### GitHub Actions Workflow

The CI/CD pipeline runs:

1. Unit tests
2. Integration tests
3. Security tests
4. Code coverage analysis
5. Test reports

### Test Reports

- **Coverage Report**: Uploaded to Codecov
- **HTML Report**: Available as build artifact
- **JSON Report**: Available for further processing

## Writing Tests

### Best Practices

1. **Use Descriptive Names**: Test names should clearly describe what is being tested
2. **Follow AAA Pattern**: Arrange, Act, Assert
3. **One Assertion Per Test**: Focus on testing one thing
4. **Use Fixtures**: Reuse setup code with fixtures
5. **Mark Tests Appropriately**: Use pytest markers (unit, integration, e2e, etc.)
6. **Clean Up**: Use fixtures for setup and teardown
7. **Test Edge Cases**: Don't just test the happy path

### Example Test Structure

```python
import pytest
from fastapi import status

@pytest.mark.integration
class TestEventAPI:
    """Test suite for Event API"""

    def test_create_event_success(self, api_client, auth_headers, event_factory):
        """Test successful event creation"""
        # Arrange
        event_data = event_factory()

        # Act
        response = api_client.post(
            "/api/v1/events",
            json=event_data,
            headers=auth_headers
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == event_data["title"]
        assert "id" in data
```

## Debugging Tests

### Run Tests in Verbose Mode

```bash
pytest -v -s
```

### Run Specific Test with Debugging

```bash
pytest tests/integration/test_auth_api.py::TestAuthenticationAPI::test_login_with_valid_credentials -v -s
```

### Use pdb for Debugging

```python
def test_something():
    import pdb; pdb.set_trace()
    # Your test code
```

### View Browser During E2E Tests

Remove `--headless` argument in conftest.py or run with visible browser flag.

## Test Coverage Goals

- **Overall Coverage**: > 80%
- **Critical Paths**: > 95%
- **API Endpoints**: 100%
- **Security Features**: 100%

## Continuous Improvement

- Add new tests for new features
- Maintain test coverage above 80%
- Review and update tests during code reviews
- Run security tests regularly
- Perform load testing before major releases

## Troubleshooting

### Common Issues

**Issue**: Selenium tests fail with "WebDriver not found"
**Solution**: The framework auto-downloads drivers. Ensure internet connectivity.

**Issue**: Tests fail with database errors
**Solution**: Ensure PostgreSQL is running and migrations are applied.

**Issue**: E2E tests timeout
**Solution**: Increase timeout in pytest.ini or check application performance.

**Issue**: Import errors in tests
**Solution**: Ensure tests are run from project root and PYTHONPATH is set correctly.

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Locust Documentation](https://docs.locust.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

## Support

For issues or questions about the testing framework, please:

1. Check this documentation
2. Review existing tests for examples
3. Open an issue on GitHub
4. Contact the development team
