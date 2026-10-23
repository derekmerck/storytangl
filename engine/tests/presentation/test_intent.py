from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from tangl.presentation.intent import (
    Accepts, Blocker, CostPreview, PieceConstraints, PlaceAccepts, UIHints,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.structuring import StructuringHandler
from tangl.presentation.values import KvRow


REFERENCE_UID = UUID("8cd4758d-9aa9-44a7-b757-17e7633e29d1")


@pytest.mark.parametrize("reference", [
    REFERENCE_UID, str(REFERENCE_UID).upper(), REFERENCE_UID.hex,
    "{" + str(REFERENCE_UID) + "}", REFERENCE_UID.urn, "packet", "Packet",
])
@pytest.mark.parametrize("model,fields", [
    (PieceConstraints, ("source_zone_ref", "target_zone_ref")),
    (PlaceAccepts, ("source_zone_ref", "target_zone_ref", "edge_ref")),
])
def test_entity_references_restore_as_uuid_identities_or_exact_labels(
    reference: UUID | str, model: type[PieceConstraints | PlaceAccepts], fields: tuple[str, ...],
) -> None:
    original = model(**dict.fromkeys(fields, reference))
    flat = Json.serialize(original.unstructure())
    assert isinstance(flat, str)
    restored = StructuringHandler.structure(Json.deserialize(flat), {model.__fqn__(): model})
    expected = reference if reference in ("packet", "Packet") else REFERENCE_UID
    for field in fields:
        assert getattr(original, field) == expected
        assert getattr(restored, field) == expected
        assert type(getattr(restored, field)) is type(expected)


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


def test_kvrow_constructor_form_round_trip_preserves_display_fields() -> None:
    row = KvRow(key="fuel", value=6, max=10, unit="gallons", hint="bar")

    assert KvRow.structure(row.unstructure()) == row


def test_blocker_preserves_portable_fields_and_optional_details() -> None:
    blocker = Blocker(
        code="needs_key",
        message="The brass key is required.",
        refs=["piece-key"],
        source="guard",
    )

    assert blocker.code == "needs_key"
    assert blocker.message == "The brass key is required."
    assert blocker.refs == ["piece-key"]
    assert blocker.source == "guard"


def test_cost_preview_is_typed_in_choice_hints_and_accepts() -> None:
    hints = UIHints(
        cost_previews=[
            CostPreview(ledger_key="purse", delta=-40, unit="silver"),
            {"ledger_key": "reputation", "delta": 1},
        ]
    )
    accepts = TypeAdapter(Accepts).validate_python(
        {
            "kind": "quantity",
            "min": 1,
            "max": 3,
            "cost_previews": [{"ledger_key": "supplies", "delta": -1, "unit": "ration"}],
        }
    )

    assert hints.cost_previews[0].ledger_key == "purse"
    assert hints.cost_previews[1].delta == 1
    assert accepts.kind == "quantity"
    assert accepts.cost_previews[0].unit == "ration"
