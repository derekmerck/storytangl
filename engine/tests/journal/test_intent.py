from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from tangl.journal.intent import Accepts, KvRow


def test_accepts_union_validates_piece_and_compose_shapes() -> None:
    adapter = TypeAdapter(Accepts)

    pieces = adapter.validate_python(
        {
            "kind": "pieces",
            "min": 1,
            "max": 2,
            "constraints": {"target_zone_ref": "zone-hand"},
        }
    )
    assert pieces.kind == "pieces"
    assert pieces.constraints is not None
    assert pieces.constraints.target_zone_ref == "zone-hand"

    compose = adapter.validate_python(
        {
            "kind": "compose",
            "parts": [
                {"role": "amount", "accepts": {"kind": "quantity", "min": 1}},
                {"role": "target", "accepts": {"kind": "pieces", "max": 1}},
            ],
        }
    )
    assert compose.kind == "compose"
    assert [part.role for part in compose.parts] == ["amount", "target"]


def test_accepts_union_rejects_old_json_schema_shape() -> None:
    adapter = TypeAdapter(Accepts)

    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "string", "enum": ["red", "blue"]})


def test_kvrow_accepts_semantic_display_fields() -> None:
    row = KvRow(key="fuel", value=6, max=10, unit="gallons", hint="bar")

    assert row.key == "fuel"
    assert row.value == 6
    assert row.max == 10
    assert row.unit == "gallons"
