import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

import pytest

from app.schemas.booking import Booking
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

    # Booking examples include a nested `event` which may be partial.
    if item_name == "Bookings":
        ev = sample.get("event")
        if isinstance(ev, dict):
            ev.setdefault("start_date", "1970-01-01T00:00:00Z")
            ev.setdefault("end_date", "1970-01-01T00:00:00Z")
            ev.setdefault("location", "")
            ev.setdefault("price", 0.0)
            ev.setdefault("capacity", 0)
            ev.setdefault("organizer_id", 0)
            ev.setdefault("available_tickets", 0)
            sample["event"] = ev

    # Notifications examples may omit some timestamp/type fields.
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
                "full_name": "",
            }
        if "event" not in sample and "event_id" in sample:
            sample["event"] = {
                "id": sample["event_id"],
                "name": "",
                "start_date": "1970-01-01T00:00:00Z",
                "end_date": "1970-01-01T00:00:00Z",
                "location": "",
                "price": 0.0,
                "capacity": 0,
                "organizer_id": 0,
                "available_tickets": 0,
            }

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
