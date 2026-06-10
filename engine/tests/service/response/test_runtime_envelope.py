from __future__ import annotations

from uuid import uuid4

from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.service.response import RuntimeEnvelope


class ExtendedRuntimeEnvelope(RuntimeEnvelope):
    diagnostic_id: str


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


def test_runtime_envelope_to_dto_uses_fragment_dto_projection() -> None:
    envelope = RuntimeEnvelope(
        cursor_id=uuid4(),
        step=1,
        fragments=[
            ContentFragment(content="Start", step=1),
            ChoiceFragment(
                edge_id=uuid4(),
                text="Buy rations.",
                accepts={"kind": "quantity", "min": 1, "max": 3},
                step=1,
            ),
        ],
    )

    payload = envelope.to_dto()
    choice = payload["fragments"][1]

    assert choice["fragment_type"] == "choice"
    assert choice["text"] == "Buy rations."
    assert choice["accepts"]["kind"] == "quantity"
    assert "seq" not in choice
    assert "step" not in choice
    assert "tags" not in choice


def test_runtime_envelope_to_dto_preserves_public_envelope_fields() -> None:
    envelope = ExtendedRuntimeEnvelope(
        step=0,
        diagnostic_id="trace-7",
        fragments=[ContentFragment(content="Start")],
    )

    payload = envelope.to_dto()

    assert payload["step"] == 0
    assert payload["diagnostic_id"] == "trace-7"
