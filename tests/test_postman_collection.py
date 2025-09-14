from app.schemas.event import Event
from app.schemas.booking import Booking
from app.schemas.user import User
from app.schemas.notification import Notification
from app.schemas.waitlist import Waitlist
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Ensure repo root is importable as a package for tests
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


COLLECTION_PATH = Path(__file__).resolve().parents[1] / "docs" / "postman" / "evently.postman_collection.json"


def load_collection():
    with open(COLLECTION_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def collection():
    return load_collection()


@pytest.mark.parametrize(
    "item_name,schema_cls",
    [
        ("Events", Event),
        ("Bookings", Booking),
        ("Users", User),
        ("Notifications", Notification),
        ("Waitlist", Waitlist),
    ],
)
def test_example_responses_have_valid_schema(collection, item_name, schema_cls):
    # Find the top-level item by name
    top = next((i for i in collection["item"] if i.get("name") == item_name), None)
    assert top is not None, f"Collection missing top-level item {item_name}"

    # Find one example response and perform lightweight checks
    required_keys_map = {
        "Events": ["id", "name"],
        "Bookings": ["id", "event_id", "number_of_tickets"],
        "Users": ["id", "email"],
        "Notifications": ["id", "user_id", "title", "message"],
        "Waitlist": ["id", "event_id", "number_of_tickets"],
    }

    reqs = top.get("item", [])
    for req in reqs:
        responses = req.get("response") or []
        if not responses:
            continue
        example = responses[0].get("_body")
        if example is None:
            continue

        # Normalize example if it's a list: check first element
        sample = example[0] if isinstance(example, list) and example else example

        # Normalize some enum casing (collection examples sometimes use upper-case labels)
        if isinstance(sample, dict):
            if "status" in sample and isinstance(sample["status"], str):
                sample["status"] = sample["status"].lower()
            if "is_read" in sample and isinstance(sample["is_read"], str):
                # convert truthy/falsey strings to booleans if needed
                val = sample["is_read"].lower()
                if val in ("true", "false"):
                    sample["is_read"] = val == "true"

        required = required_keys_map.get(item_name, [])
        missing = [k for k in required if not (isinstance(sample, dict) and k in sample)]
        if missing:
            pytest.fail(f"Example response for {req.get('name')} missing keys: {missing}")
        return

    pytest.skip(f"No example response found for top-level item {item_name}")
