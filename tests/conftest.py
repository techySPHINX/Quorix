"""
Comprehensive Test Configuration and Fixtures
Provides fixtures for database, API client, Selenium browser, and test data
"""

from app.main import app
from app.database import Base, get_database
from app.core.config import Settings
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# Initialize Faker
fake = Faker()

# Test Database Configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///./test.db"
)
TEST_SYNC_DATABASE_URL = os.getenv(
    "TEST_SYNC_DATABASE_URL", "sqlite:///./test.db"
)


# ============================================
# Session Scope Fixtures
# ============================================


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing"""
    return Settings(
        SQLALCHEMY_DATABASE_URI=TEST_DATABASE_URL,
        REDIS_URL="redis://localhost:6379/1",
        SECRET_KEY="test-secret-key-for-testing-only",
    )


# ============================================
# Database Fixtures
# ============================================


@pytest.fixture(scope="function")
async def async_db_engine():
    """Create async database engine for tests"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests"""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session_maker = async_sessionmaker(
        async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def sync_db_engine():
    """Create sync database engine for tests"""
    engine = create_engine(TEST_SYNC_DATABASE_URL, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sync_db_session(sync_db_engine) -> Generator[Session, None, None]:
    """Create sync database session for tests"""
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=sync_db_engine
    )
    session = SessionLocal()
    yield session
    session.close()


# ============================================
# API Client Fixtures
# ============================================


@pytest.fixture(scope="function")
def api_client(sync_db_session) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with database override"""

    def override_get_db():
        try:
            yield sync_db_session
        finally:
            pass

    app.dependency_overrides[get_database] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_api_client(async_db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for tests"""

    async def override_get_db():
        yield async_db_session

    app.dependency_overrides[get_database] = override_get_db

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


# ============================================
# Selenium Browser Fixtures
# ============================================


@pytest.fixture(scope="session")
def browser_type(request) -> str:
    """Get browser type from command line or default to chrome"""
    return request.config.getoption("--browser", default="chrome")


@pytest.fixture(scope="function")
def browser(browser_type) -> Generator[webdriver.Remote, None, None]:
    """Create Selenium WebDriver instance"""
    driver = None
    try:
        if browser_type.lower() == "chrome":
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-popup-blocking")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        elif browser_type.lower() == "firefox":
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=firefox_options)
        else:
            raise ValueError(f"Unsupported browser: {browser_type}")
        driver.implicitly_wait(10)
        yield driver
    finally:
        if driver:
            driver.quit()


@pytest.fixture(scope="function")
def base_url() -> str:
    """Base URL for E2E tests"""
    return os.getenv("TEST_BASE_URL") or "http://localhost:8000"


# ============================================
# Test Data Factories
# ============================================


@pytest.fixture
def user_factory():
    """Factory for creating test user data"""
    def _create_user(**kwargs):
        return {
            "email": kwargs.get("email", fake.email()),
            "username": kwargs.get("username", fake.user_name()),
            "password": kwargs.get("password", "TestPassword123!"),
            "full_name": kwargs.get("full_name", fake.name()),
            "is_active": kwargs.get("is_active", True),
            "is_superuser": kwargs.get("is_superuser", False),
        }
    return _create_user


@pytest.fixture
def event_factory():
    """Factory for creating test event data"""
    def _create_event(**kwargs):
        return {
            "title": kwargs.get("title", fake.sentence(nb_words=4)),
            "description": kwargs.get("description", fake.text(max_nb_chars=200)),
            "location": kwargs.get("location", fake.address()),
            "start_time": kwargs.get("start_time", fake.future_datetime()),
            "end_time": kwargs.get("end_time", fake.future_datetime()),
            "max_attendees": kwargs.get("max_attendees", fake.random_int(10, 100)),
            "is_public": kwargs.get("is_public", True),
        }
    return _create_event


@pytest.fixture
def booking_factory():
    """Factory for creating test booking data"""
    def _create_booking(**kwargs):
        return {
            "event_id": kwargs.get("event_id"),
            "user_id": kwargs.get("user_id"),
            "status": kwargs.get("status", "confirmed"),
            "num_tickets": kwargs.get("num_tickets", 1),
        }
    return _create_booking


# ============================================
# Authentication Helpers
# ============================================


@pytest.fixture
def auth_token(api_client, user_factory):
    """Create authenticated user and return JWT token"""
    user_data = user_factory()

    # Register user
    response = api_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code in [200, 201]

    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }
    response = api_client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Generate authorization headers with JWT token"""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================
# Mock Fixtures
# ============================================


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for tests"""
    mock = MagicMock()
    mock.delay.return_value = MagicMock(id="test-task-id")
    mock.apply_async.return_value = MagicMock(id="test-task-id")
    return mock


# ============================================
# Pytest Configuration
# ============================================


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--browser",
        action="store",
        default="chrome",
        help="Browser to use for E2E tests: chrome or firefox",
    )
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8000",
        help="Base URL for E2E tests",
    )
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers and options"""
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="need --slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
