"""Tests for the typed PieceFragment graduation.

Pins the serialized shape to the established conformance-fixture convention
(`fragment_type="piece"`, flat `piece_id`/`kind`/`content`/`display_state`/
`zone_ref`, and `hints.label_text`).
"""

from __future__ import annotations

from uuid import UUID

from tangl.journal.fragments import (
    PieceFragment,
    PresentationHints,
    fragment_to_dto,
)


def test_piece_fragment_serializes_to_fixture_shape() -> None:
    uid = UUID("00000000-0000-4000-8000-000000000504")
    zone = UUID("00000000-0000-4000-8000-000000000503")
    piece = PieceFragment(
        uid=uid,
        piece_id="lamp",
        piece_kind="item",
        content="brass lamp",
        display_state="available",
        zone_ref=zone,
        hints=PresentationHints(label_text="brass lamp"),
    )

    data = fragment_to_dto(piece)

    assert data["fragment_type"] == "piece"
    assert data["piece_id"] == "lamp"
    assert data["kind"] == "item"
    assert data["content"] == "brass lamp"
    assert data["display_state"] == "available"
    assert str(data["zone_ref"]) == str(zone)
    assert data["hints"]["label_text"] == "brass lamp"


def test_piece_fragment_carries_properties_for_richer_kinds() -> None:
    piece = PieceFragment(
        piece_id="candidate-0",
        piece_kind="candidate",
        content="Bek Tarsus",
        properties={"declared_purpose": "merchant", "declared_origin": "Kalden"},
        hints=PresentationHints(label_text="Bek Tarsus (merchant)"),
    )

    data = piece.model_dump(mode="json", by_alias=True, exclude_none=True)

    assert data["properties"]["declared_purpose"] == "merchant"
    assert data["piece_kind"] == "candidate"
    assert data["hints"]["label_text"] == "Bek Tarsus (merchant)"


def test_piece_kind_survives_constructor_form_round_trip() -> None:
    piece = PieceFragment(
        piece_id="candidate-0",
        piece_kind="candidate",
        content="Bek Tarsus",
    )

    restored = PieceFragment.structure(piece.unstructure())

    assert isinstance(restored, PieceFragment)
    assert restored.piece_kind == "candidate"
