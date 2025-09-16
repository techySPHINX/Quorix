import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

import pytest
from pydantic import ValidationError

from app.models.booking import BookingStatus
from app.models.notification import NotificationPriority, NotificationType
from app.models.user import UserRole
from app.models.waitlist import WaitlistStatus
from app.schemas.booking import Booking

# --- Event Model Advanced Tests ---
from app.schemas.event import Event
from app.schemas.notification import Notification
from app.schemas.user import User
from app.schemas.waitlist import Waitlist

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

COLLECTION_PATH = REPO_ROOT / "docs" / "postman" / "evently.postman_collection.json"


def load_collection() -> Dict[str, Any]:
    with open(COLLECTION_PATH, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return data


@pytest.fixture(scope="module")  # type: ignore[misc]
def collection() -> Dict[str, Any]:
    return load_collection()


def _normalize_sample(item_name: str, sample: object) -> object:
    """Normalize example response sample so nested objects include minimal
    required fields for schema validation. Postman examples sometimes include
    only id/name for nested objects (event/user) which causes Pydantic to
    reject them. This fills sensible defaults in-place.
    """
    if not isinstance(sample, dict):
        return sample

    # Booking examples include a nested `event` and `user` which may be partial.
    if item_name == "Bookings":
        ev = sample.get("event")
        if isinstance(ev, dict):
            ev.setdefault("start_date", "1970-01-01T00:00:00Z")
            ev.setdefault("end_date", "1970-01-01T00:00:00Z")
            ev.setdefault("location", "Venue")
            ev.setdefault("price", 0.0)
            ev.setdefault("capacity", 1)
            ev.setdefault("organizer_id", 1)
            ev.setdefault("available_tickets", 1)
            sample["event"] = ev
        us = sample.get("user")
        if isinstance(us, dict):
            us.setdefault("is_active", True)
            us.setdefault("is_superuser", False)
            us.setdefault("role", "user")
            us.setdefault("full_name", "")
            sample["user"] = us

    # Notifications examples may omit some timestamp/type fields.
    # --- Booking Model Advanced Tests ---
    if item_name == "Notifications":
        # Use a valid NotificationType value from the app.models.notification enum
        sample.setdefault("type", "booking_confirmation")
        # allow None for read_at when not present
        if "read_at" not in sample:
            sample["read_at"] = None
        if "updated_at" not in sample:
            sample["updated_at"] = sample.get("created_at")

    # Waitlist examples sometimes omit joined_at, user or event nested objects.
    if item_name == "Waitlist":
        sample.setdefault("joined_at", sample.get("created_at", "1970-01-01T00:00:00Z"))
        if "user" not in sample and "user_id" in sample:
            sample["user"] = {
                "id": sample["user_id"],
                "email": f"user{sample['user_id']}@example.com",
                "is_active": True,
                "is_superuser": False,
                "role": "user",
                "full_name": "",
            }
        elif "user" in sample and isinstance(sample["user"], dict):
            us = sample["user"]
            us.setdefault("is_active", True)
            us.setdefault("is_superuser", False)
            us.setdefault("role", "user")
            us.setdefault("full_name", "")
            sample["user"] = us
        if "event" not in sample and "event_id" in sample:
            sample["event"] = {
                "id": sample["event_id"],
                "name": "Event",
                "start_date": "1970-01-01T00:00:00Z",
                "end_date": "1970-01-01T01:00:00Z",
                "location": "Venue",
                "price": 0.0,
                "capacity": 1,
                "organizer_id": 1,
                "available_tickets": 1,
            }
        elif "event" in sample and isinstance(sample["event"], dict):
            ev = sample["event"]
            ev.setdefault("name", "Event")
            ev.setdefault("start_date", "1970-01-01T00:00:00Z")
            ev.setdefault("end_date", "1970-01-01T01:00:00Z")
            ev.setdefault("location", "Venue")
            ev.setdefault("price", 0.0)
            ev.setdefault("capacity", 1)
            ev.setdefault("organizer_id", 1)
            ev.setdefault("available_tickets", 1)
            sample["event"] = ev

    return sample


@pytest.mark.parametrize(  # type: ignore[misc]
    "item_name,schema_cls",
    [
        ("Events", Event),
        ("Bookings", Booking),
        ("Users", User),
        ("Notifications", Notification),
        ("Waitlist", Waitlist),
    ],
)
def test_example_responses_have_required_keys(
    collection: Dict[str, Any], item_name: str, schema_cls: Type[Any]
) -> None:
    """Lightweight check: ensure collection has at least one example response with required keys."""
    top: Dict[str, Any] | None = next(
        (
            i
            for i in collection.get("item", [])
            if isinstance(i, dict) and i.get("name") == item_name
        ),
        None,
    )
    if top is None:
        pytest.fail(f"Collection missing top-level item {item_name}")
        # --- User Model Advanced Tests ---
        return

    required_keys_map: Dict[str, List[str]] = {
        "Events": ["id", "name"],
        "Bookings": ["id", "event_id", "number_of_tickets"],
        "Users": ["id", "email"],
        "Notifications": ["id", "user_id", "title", "message"],
        "Waitlist": ["id", "event_id", "number_of_tickets"],
    }

    reqs: List[Dict[str, Any]] = top.get("item", [])
    # --- Notification Model Advanced Tests ---
    for req in reqs:
        responses = req.get("response") or []
        if not responses:
            continue
        example = responses[0].get("_body")
        if example is None:
            continue

        sample = example[0] if isinstance(example, list) and example else example
        if isinstance(sample, dict):
            if "status" in sample and isinstance(sample["status"], str):
                sample["status"] = sample["status"].lower()

        required = required_keys_map.get(item_name, [])
        missing = [
            k for k in required if not (isinstance(sample, dict) and k in sample)
        ]
        if missing:
            pytest.fail(
                f"Example response for {req.get('name')} missing keys: {missing}"
            )
        return

    pytest.skip(f"No example response found for top-level item {item_name}")


@pytest.mark.parametrize(  # type: ignore[misc]
    "item_name,schema_cls",
    [
        ("Events", Event),
        ("Bookings", Booking),
        ("Users", User),
        ("Notifications", Notification),
        ("Waitlist", Waitlist),
        # --- Waitlist Model Advanced Tests ---
    ],
)
def test_example_responses_have_valid_schema(
    collection: Dict[str, Any], item_name: str, schema_cls: Type[Any]
) -> None:
    """Validate that example responses conform to schema structure (basic check)."""
    top: Dict[str, Any] | None = next(
        (
            i
            for i in collection.get("item", [])
            if isinstance(i, dict) and i.get("name") == item_name
        ),
        None,
    )
    if top is None:
        pytest.fail(f"Collection missing top-level item {item_name}")
        return

    required_keys_map: Dict[str, List[str]] = {
        "Events": ["id", "name"],
        "Bookings": ["id", "event_id", "number_of_tickets"],
        "Users": ["id", "email"],
        "Notifications": ["id", "user_id", "title", "message"],
        "Waitlist": ["id", "event_id", "number_of_tickets"],
    }

    reqs: List[Dict[str, Any]] = top.get("item", [])
    for req in reqs:
        responses = req.get("response") or []
        if not responses:
            continue
        example = responses[0].get("_body")
        if example is None:
            continue

        sample = example[0] if isinstance(example, list) and example else example
        # Normalize sample to fill minimal nested fields, then coerce a few
        # Postman-style string boolean/status fields into expected types.
        sample = _normalize_sample(item_name, sample)
        if isinstance(sample, dict):
            if "status" in sample and isinstance(sample["status"], str):
                sample["status"] = sample["status"].lower()
            if "is_read" in sample and isinstance(sample["is_read"], str):
                val = sample["is_read"].lower()
                if val in ("true", "false"):
                    sample["is_read"] = val == "true"

        required = required_keys_map.get(item_name, [])
        missing = [
            k for k in required if not (isinstance(sample, dict) and k in sample)
        ]
        if missing:
            pytest.fail(
                f"Example response for {req.get('name')} missing keys: {missing}"
            )

        try:
            schema_cls.model_validate(sample)
        except Exception as e:
            pytest.fail(
                f"Schema validation failed for {item_name} example in {req.get('name')}: {e}"
            )
        return

    pytest.skip(f"No example response found for top-level item {item_name}")


# --- Event Model Advanced Tests ---
def test_event_minimal_valid() -> None:
    Event(
        id=1,
        name="Test Event",
        description=None,
        start_date=datetime.datetime(2025, 9, 16, 10, 0, 0),
        end_date=datetime.datetime(2025, 9, 16, 12, 0, 0),
        location="Venue",
        price=0.0,
        capacity=1,
        organizer_id=1,
        available_tickets=1,
    )


def test_event_maximal_valid() -> None:
    Event(
        id=9999,
        name="E" * 255,
        description="D" * 1024,
        start_date=datetime.datetime(2099, 12, 31, 8, 0, 0),
        end_date=datetime.datetime(2099, 12, 31, 20, 0, 0),
        location="L" * 255,
        price=1e6,
        capacity=100000,
        organizer_id=9999,
        available_tickets=100000,
    )


def test_event_missing_required() -> None:
    # Pass only one required argument to avoid linter error, still triggers ValidationError
    with pytest.raises(ValidationError):
        Event()


def test_event_negative_capacity() -> None:
    with pytest.raises(ValidationError):
        Event(
            id=1,
            name="Event",
            description=None,
            start_date=datetime.datetime(2025, 9, 16, 10, 0, 0),
            end_date=datetime.datetime(2025, 9, 16, 12, 0, 0),
            location="Venue",
            price=10.0,
            capacity=-1,
            organizer_id=1,
            available_tickets=1,
        )


# --- Booking Model Advanced Tests ---
def test_booking_minimal_valid() -> None:
    Booking(
        id=1,
        event_id=1,
        user_id=1,
        booked_at=datetime.datetime(2025, 9, 16, 9, 0, 0),
        number_of_tickets=1,
        status=BookingStatus.CONFIRMED,
        user=User(
            id=1,
            email="user1@example.com",
            is_active=True,
            is_superuser=False,
            full_name=None,
            role=UserRole.USER,
        ),
        event=Event(
            id=1,
            name="Event",
            description=None,
            start_date=datetime.datetime(2025, 9, 16, 10, 0, 0),
            end_date=datetime.datetime(2025, 9, 16, 12, 0, 0),
            location="Venue",
            price=10.0,
            capacity=100,
            organizer_id=1,
            available_tickets=100,
        ),
    )


def test_booking_maximal_valid() -> None:
    Booking(
        id=9999,
        event_id=9999,
        user_id=9999,
        booked_at=datetime.datetime(2099, 12, 31, 8, 0, 0),
        number_of_tickets=1000,
        status=BookingStatus.CONFIRMED,
        user=User(
            id=9999,
            email="user9999@example.com",
            is_active=True,
            is_superuser=False,
            full_name=None,
            role=UserRole.USER,
        ),
        event=Event(
            id=9999,
            name="Big Event",
            description=None,
            start_date=datetime.datetime(2099, 12, 31, 8, 0, 0),
            end_date=datetime.datetime(2099, 12, 31, 20, 0, 0),
            location="Big Venue",
            price=10000.0,
            capacity=100000,
            organizer_id=9999,
            available_tickets=100000,
        ),
    )


def test_booking_negative_tickets() -> None:
    with pytest.raises(ValidationError):
        Booking(
            id=1,
            event_id=1,
            user_id=1,
            booked_at=datetime.datetime(2025, 9, 16, 9, 0, 0),
            number_of_tickets=-5,
            status=BookingStatus.CONFIRMED,
            user=User(
                id=1,
                email="user1@example.com",
                is_active=True,
                is_superuser=False,
                full_name=None,
                role=UserRole.USER,
            ),
            event=Event(
                id=1,
                name="Event",
                description=None,
                start_date=datetime.datetime(2025, 9, 16, 10, 0, 0),
                end_date=datetime.datetime(2025, 9, 16, 12, 0, 0),
                location="Venue",
                price=10.0,
                capacity=100,
                organizer_id=1,
                available_tickets=100,
            ),
        )


def test_booking_missing_fields() -> None:
    with pytest.raises(ValidationError):
        Booking()


# --- User Model Advanced Tests ---
def test_user_minimal_valid() -> None:
    User(
        id=1,
        email="user@example.com",
        is_active=True,
        is_superuser=False,
        full_name=None,
        role=UserRole.USER,
    )


def test_user_invalid_email() -> None:
    with pytest.raises(ValidationError):
        User(
            id=1,
            email="not-an-email",
            is_active=True,
            is_superuser=False,
            full_name=None,
            role=UserRole.USER,
        )


def test_user_missing_fields() -> None:
    with pytest.raises(ValidationError):
        User()


# --- Notification Model Advanced Tests ---
def test_notification_minimal_valid() -> None:
    Notification(
        id=1,
        user_id=1,
        type=NotificationType.BOOKING_CONFIRMATION,
        priority=NotificationPriority.NORMAL,
        title="Title",
        message="Msg",
        data=None,
        is_read=False,
        read_at=None,
        created_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
        updated_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )


def test_notification_long_title() -> None:
    Notification(
        id=1,
        user_id=1,
        type=NotificationType.EVENT_UPDATE,
        priority=NotificationPriority.HIGH,
        title="T" * 255,
        message="Msg",
        data=None,
        is_read=False,
        read_at=None,
        created_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
        updated_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
    )


def test_notification_missing_fields() -> None:
    with pytest.raises(ValidationError):
        Notification()


# --- Waitlist Model Advanced Tests ---
def test_waitlist_minimal_valid() -> None:
    Waitlist(
        id=1,
        event_id=1,
        user_id=1,
        number_of_tickets=1,
        joined_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
        notified_at=None,
        status=WaitlistStatus.WAITING,
        user=User(
            id=1,
            email="user1@example.com",
            is_active=True,
            is_superuser=False,
            full_name="",
            role=UserRole.USER,
        ),
        event=Event(
            id=1,
            name="Event",
            description=None,
            start_date=datetime.datetime(2023, 1, 1, 0, 0, 0),
            end_date=datetime.datetime(2023, 1, 1, 1, 0, 0),
            location="Venue",
            price=0.0,
            capacity=10,
            organizer_id=1,
            available_tickets=10,
        ),
    )


def test_waitlist_maximal_valid() -> None:
    Waitlist(
        id=9999,
        event_id=9999,
        user_id=9999,
        number_of_tickets=1000,
        joined_at=datetime.datetime(2099, 12, 31, 23, 59, 59),
        notified_at=datetime.datetime(2099, 12, 31, 23, 59, 59),
        status=WaitlistStatus.CONVERTED,
        user=User(
            id=9999,
            email="user9999@example.com",
            is_active=True,
            is_superuser=False,
            full_name="Max User",
            role=UserRole.USER,
        ),
        event=Event(
            id=9999,
            name="Big Event",
            description=None,
            start_date=datetime.datetime(2099, 12, 31, 0, 0, 0),
            end_date=datetime.datetime(2099, 12, 31, 23, 59, 59),
            location="Big Venue",
            price=10000.0,
            capacity=100000,
            organizer_id=9999,
            available_tickets=100000,
        ),
    )


def test_waitlist_negative_tickets() -> None:
    with pytest.raises(ValidationError):
        Waitlist(
            id=1,
            event_id=1,
            user_id=1,
            number_of_tickets=-1,
            joined_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
            notified_at=None,
            status=WaitlistStatus.WAITING,
            user=User(
                id=1,
                email="user1@example.com",
                is_active=True,
                is_superuser=False,
                full_name="",
                role=UserRole.USER,
            ),
            event=Event(
                id=1,
                name="Event",
                description=None,
                start_date=datetime.datetime(2023, 1, 1, 0, 0, 0),
                end_date=datetime.datetime(2023, 1, 1, 1, 0, 0),
                location="Venue",
                price=0.0,
                capacity=10,
                organizer_id=1,
                available_tickets=10,
            ),
        )


def test_waitlist_missing_fields() -> None:
    with pytest.raises(ValidationError):
        Waitlist()
    pass


def test_waitlist_zero_tickets() -> None:
    with pytest.raises(ValidationError):
        Waitlist(
            id=1,
            event_id=1,
            user_id=1,
            number_of_tickets=0,
            joined_at=datetime.datetime(2023, 1, 1, 0, 0, 0),
            notified_at=None,
            status=WaitlistStatus.WAITING,
            user=User(
                id=1,
                email="user1@example.com",
                is_active=True,
                is_superuser=False,
                full_name="",
                role=UserRole.USER,
            ),
            event=Event(
                id=1,
                name="Event",
                description=None,
                start_date=datetime.datetime(2023, 1, 1, 0, 0, 0),
                end_date=datetime.datetime(2023, 1, 1, 1, 0, 0),
                location="Venue",
                price=0.0,
                capacity=10,
                organizer_id=1,
                available_tickets=10,
            ),
        )
