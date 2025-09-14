import json
from pathlib import Path

import pytest

from pydantic import ValidationError

# Import schemas
from app.schemas.event import Event
from app.schemas.booking import Booking
from app.schemas.user import User, Token
from app.schemas.notification import Notification
from app.schemas.waitlist import Waitlist

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

    # Find one example response and validate against schema
    for req in top.get("item", []):
        responses = req.get("response") or []
        if not responses:
            continue
        example = responses[0].get("_body")
        if example is None:
            continue
        # If response is a list, validate first element against the schema where appropriate
        try:
            if isinstance(example, list):
                for elem in example:
                    schema_cls.model_validate(elem)
            else:
                schema_cls.model_validate(example)
        except ValidationError as e:
            pytest.fail(f"Example response for {req.get('name')} failed schema validation: {e}")
        return

    pytest.skip(f"No example response found for top-level item {item_name}")
