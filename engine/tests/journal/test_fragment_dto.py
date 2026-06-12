"""Tests for client-facing fragment DTO projection and hydration.

Coverage includes bookkeeping omission, typed fragment round trips, aliases,
unknown-fragment fallback, and discriminator validation.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from tangl.core import BaseFragment
from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    PieceFragment,
    fragment_from_dto,
    fragment_to_dto,
)
from tangl.journal.intent import Blocker, CostPreview, UIHints


def test_fragment_to_dto_omits_stream_bookkeeping() -> None:
    fragment = ChoiceFragment(
        edge_id=uuid4(),
        text="Take the brass lamp.",
        step=4,
    )

    payload = fragment_to_dto(fragment)

    assert payload["fragment_type"] == "choice"
    assert payload["text"] == "Take the brass lamp."
    assert "seq" not in payload
    assert "step" not in payload
    assert "tags" not in payload


def test_choice_blocker_dto_round_trip_preserves_typed_contract() -> None:
    fragment = ChoiceFragment(
        edge_id=uuid4(),
        text="Unlock the door.",
        available=False,
        blockers=[
            Blocker(
                code="needs_key",
                message="The brass key is required.",
                refs=["piece-key"],
            )
        ],
    )

    payload = fragment_to_dto(fragment)
    restored = fragment_from_dto(payload)

    assert payload["blockers"] == [
        {
            "code": "needs_key",
            "message": "The brass key is required.",
            "refs": ["piece-key"],
        }
    ]
    assert isinstance(restored, ChoiceFragment)
    assert restored.blockers is not None
    assert restored.blockers[0].code == "needs_key"


def test_choice_cost_preview_dto_round_trip_preserves_typed_contract() -> None:
    fragment = ChoiceFragment(
        edge_id=uuid4(),
        text="Buy the lamp.",
        ui_hints=UIHints(
            cost_previews=[
                CostPreview(ledger_key="purse", delta=-40, unit="silver"),
                CostPreview(ledger_key="reputation", delta=1),
            ]
        ),
    )

    payload = fragment_to_dto(fragment)
    restored = fragment_from_dto(payload)

    assert payload["ui_hints"]["cost_previews"] == [
        {"ledger_key": "purse", "delta": -40, "unit": "silver"},
        {"ledger_key": "reputation", "delta": 1},
    ]
    assert isinstance(restored, ChoiceFragment)
    assert restored.ui_hints is not None
    assert restored.ui_hints.cost_previews[0].ledger_key == "purse"
    assert restored.ui_hints.cost_previews[1].delta == 1


def test_fragment_to_dto_preserves_piece_kind() -> None:
    fragment = PieceFragment(
        piece_id="permit-a17",
        piece_kind="document",
        content="Permit A17",
    )

    payload = fragment_to_dto(fragment)

    assert payload["fragment_type"] == "piece"
    assert payload["kind"] == "document"
    assert "piece_kind" not in payload


def test_fragment_from_dto_maps_piece_kind_to_engine_field() -> None:
    fragment = fragment_from_dto(
        {
            "fragment_type": "piece",
            "piece_id": "permit-a17",
            "kind": "document",
            "content": "Permit A17",
        }
    )

    assert isinstance(fragment, PieceFragment)
    assert fragment.piece_kind == "document"


def test_fragment_to_dto_omits_redundant_type_alias() -> None:
    fragment = AttributedFragment(
        content="Keep moving.",
        who="guide",
        how="whispers",
        media="",
    )

    payload = fragment_to_dto(fragment)

    assert payload["fragment_type"] == "attributed"
    assert "type" not in payload


def test_fragment_from_dto_hydrates_known_fragment() -> None:
    edge_id = UUID("00000000-0000-4000-8000-000000000111")

    fragment = fragment_from_dto(
        {
            "fragment_type": "choice",
            "edge_id": str(edge_id),
            "text": "Continue.",
        }
    )

    assert isinstance(fragment, ChoiceFragment)
    assert fragment.edge_id == edge_id
    assert fragment.text == "Continue."


def test_fragment_from_dto_preserves_unknown_fragment_payload() -> None:
    fragment = fragment_from_dto({"fragment_type": "future_card", "foo": "bar"})

    assert isinstance(fragment, BaseFragment)
    assert fragment.fragment_type == "future_card"
    assert fragment.content == {"fragment_type": "future_card", "foo": "bar"}


def test_known_fragment_dto_validation_stays_strict() -> None:
    with pytest.raises(ValidationError) as exc_info:
        fragment_from_dto({"fragment_type": "piece", "content": "missing id"})

    assert "piece_id" in str(exc_info.value)


def test_typed_content_fragment_rejects_extension_discriminator() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ContentFragment(fragment_type="custom_card", content="Use BaseFragment instead")

    assert "content" in str(exc_info.value)
