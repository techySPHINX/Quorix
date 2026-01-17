# Quick Start: Running Evently Tests

## Prerequisites

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

## Basic Testing

### 1. Run All Tests

```bash
pytest
```

### 2. Run with Coverage

```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser to view report
```

### 3. Run Specific Categories

```bash
# Unit tests (fast)
pytest -m unit

# Integration tests (medium speed)
pytest -m integration

# End-to-end tests (slow, requires app running)
pytest -m e2e

# Security tests
pytest -m security
```

### 4. Run Tests in Parallel (Faster)

```bash
pytest -n auto
```

## Using Test Scripts

### Windows (PowerShell)

```powershell
# Run all tests
.\scripts\run_tests.ps1

# With coverage
.\scripts\run_tests.ps1 -Coverage

# Specific category
.\scripts\run_tests.ps1 -Category integration

# E2E with Firefox
.\scripts\run_tests.ps1 -Category e2e -Browser firefox
```

### Linux/Mac

```bash
# Run all tests
python scripts/run_tests.py

# With coverage
python scripts/run_tests.py --coverage

# Specific category
python scripts/run_tests.py --category integration
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
# Chrome (default)
pytest tests/e2e/ --browser=chrome

# Firefox
pytest tests/e2e/ --browser=firefox
```

## Performance Testing

```bash
# Start Locust web UI
locust -f tests/performance/locustfile.py

# Open http://localhost:8089
# Set number of users and spawn rate
# Click "Start swarming"
```

## Docker Testing

```bash
# Run all tests in Docker
docker-compose -f infrastructure/docker/docker-compose.test.yml up test-runner

# Run E2E tests in Docker
docker-compose -f infrastructure/docker/docker-compose.test.yml up e2e-runner
```

## Common Issues

### Issue: "No module named 'app'"

**Solution**: Run from project root directory

```bash
cd c:\Users\KIIT\Desktop\open-source\evently
pytest
```

### Issue: Database connection error

**Solution**: Ensure PostgreSQL is running

```bash
docker-compose up -d postgres
```

### Issue: Redis connection error

**Solution**: Ensure Redis is running

```bash
docker-compose up -d redis
```

### Issue: Selenium/WebDriver errors

**Solution**: Selenium auto-downloads drivers. Ensure internet connection.

## Test Results

### View Coverage Report

```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html
```

### View Test Report

```bash
pytest --html=report.html --self-contained-html
# Open report.html
```

## Tips

- Use `-v` for verbose output
- Use `-s` to see print statements
- Use `-x` to stop on first failure
- Use `-k "test_name"` to run specific test
- Use `--lf` to run last failed tests
- Use `--maxfail=3` to stop after 3 failures

## Example Workflow

```bash
# 1. Make code changes
# 2. Run quick tests
pytest -m unit -x

# 3. Run integration tests
pytest -m integration

# 4. Run with coverage
pytest --cov=app --cov-report=term

# 5. If all pass, run full suite
pytest

# 6. Before commit, run all
.\scripts\run_tests.ps1 -Coverage
```

## Next Steps

- Read full documentation: `docs/TESTING.md`
- View implementation details: `docs/TESTING_IMPLEMENTATION.md`
- Check CI/CD setup: `.github/workflows/main.yml`
