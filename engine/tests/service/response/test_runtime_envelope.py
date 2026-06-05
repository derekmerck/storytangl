from __future__ import annotations

from uuid import uuid4

from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.service.response import RuntimeEnvelope


def test_runtime_envelope_model_dump_preserves_fragment_subclass_fields() -> None:
    edge_id = uuid4()
    envelope = RuntimeEnvelope(
        cursor_id=uuid4(),
        step=1,
        fragments=[
            ContentFragment(content="Start"),
            ChoiceFragment(
                edge_id=edge_id,
                text="Buy rations.",
                accepts={
                    "kind": "quantity",
                    "min": 1,
                    "max": 3,
                    "unit": "ration",
                },
                ui_hints={"hotkey": "b", "source_kind": "market"},
            ),
        ],
    )

    payload = envelope.model_dump(mode="json", by_alias=True, exclude_none=True)
    choice = payload["fragments"][1]

    assert choice["fragment_type"] == "choice"
    assert choice["edge_id"] == str(edge_id)
    assert choice["text"] == "Buy rations."
    assert choice["accepts"]["kind"] == "quantity"
    assert choice["accepts"]["unit"] == "ration"
    assert choice["ui_hints"]["hotkey"] == "b"
    assert choice["ui_hints"]["source_kind"] == "market"
