import json
from pathlib import Path
from typing import Any, Dict, Optional, Type

import pytest
from pydantic import ValidationError

# Import schemas
from app.schemas.booking import Booking
from app.schemas.event import Event
from app.schemas.notification import Notification
from app.schemas.user import User
from app.schemas.waitlist import Waitlist

COLLECTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "postman"
    / "evently.postman_collection.json"
)


def load_collection() -> Dict[str, Any]:
    data: Dict[str, Any] = json.load(open(COLLECTION_PATH, "r", encoding="utf-8"))
    return data


@pytest.fixture(scope="module")  # type: ignore[misc]
def collection() -> Dict[str, Any]:
    return load_collection()


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
    """Validate example responses against Pydantic schemas where possible."""
    top: Optional[Dict[str, Any]] = next(
        (
            i
            for i in collection.get("item", [])
            if isinstance(i, dict) and i.get("name") == item_name
        ),
        None,
    )
    if top is None:
        pytest.fail(f"Collection missing top-level item {item_name}")

    if top is not None:
        for req in top.get("item", []):  # safe because top is Dict[str, Any]
            if not isinstance(req, dict):
                continue
            responses = req.get("response") or []
            if not responses:
                continue
            example = (
                responses[0].get("_body") if isinstance(responses[0], dict) else None
            )
            if example is None:
                continue

            try:
                if isinstance(example, list):
                    for elem in example:
                        schema_cls.model_validate(elem)
                else:
                    schema_cls.model_validate(example)
            except ValidationError as exc:
                pytest.fail(
                    f"Example response for {req.get('name')} failed schema validation: {exc}"
                )

            return None  # validate only first found example

    pytest.skip(f"No example response found for top-level item {item_name}")
