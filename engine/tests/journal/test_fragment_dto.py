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


def test_fragment_to_dto_preserves_piece_kind() -> None:
    fragment = PieceFragment(
        piece_id="permit-a17",
        kind="document",
        content="Permit A17",
    )

    payload = fragment_to_dto(fragment)

    assert payload["fragment_type"] == "piece"
    assert payload["kind"] == "document"


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
