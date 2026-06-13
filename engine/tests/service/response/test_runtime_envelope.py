from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.service.response import (
    CommandEdgeQuery,
    EdgeResolutionRequest,
    GrammarHint,
    RuntimeEnvelope,
    RuntimeEnvelopePayload,
    UxEvent,
)


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


def test_runtime_envelope_payload_validates_dto_without_restoring_bookkeeping() -> None:
    envelope = RuntimeEnvelope(
        fragments=[
            ContentFragment(content="Start", step=1),
            ChoiceFragment(edge_id=uuid4(), text="Continue", step=1),
        ],
    )

    payload = RuntimeEnvelopePayload.model_validate(envelope.to_dto()).model_dump(
        mode="json",
        exclude_none=True,
    )

    assert payload["fragments"][0]["content"] == "Start"
    assert "seq" not in payload["fragments"][0]
    assert "tags" not in payload["fragments"][0]
    assert "step" not in payload["fragments"][0]


def test_runtime_envelope_to_dto_preserves_public_envelope_fields() -> None:
    envelope = ExtendedRuntimeEnvelope(
        step=0,
        diagnostic_id="trace-7",
        fragments=[ContentFragment(content="Start")],
    )

    payload = envelope.to_dto()

    assert payload["step"] == 0
    assert payload["diagnostic_id"] == "trace-7"


def test_runtime_envelope_to_dto_keeps_ux_events_outside_journal_fragments() -> None:
    envelope = RuntimeEnvelope(
        fragments=[ContentFragment(content="Start")],
        ux_events=[
            UxEvent(
                event_type="edge_not_found",
                message="I couldn't match that command.",
                presentation="inline",
                replay=False,
                severity="warning",
            )
        ],
    )

    payload = envelope.to_dto()

    assert len(payload["fragments"]) == 1
    assert payload["ux_events"][0]["event_type"] == "edge_not_found"
    assert payload["ux_events"][0]["presentation"] == "inline"
    assert payload["ux_events"][0]["replay"] is False


def test_runtime_envelope_hydrates_typed_grammar_metadata() -> None:
    envelope = RuntimeEnvelope(
        fragments=[],
        metadata={
            "fixture": "command_hints",
            "grammar": {
                "verbs": [
                    {
                        "verb": "take",
                        "aliases": ["get"],
                        "frames": ["Take the brass lamp."],
                    }
                ],
                "nouns": [
                    {
                        "noun": "brass lamp",
                        "aliases": ["lamp"],
                        "piece_ids": ["lamp"],
                    }
                ],
                "placeholder": "Try: take lamp",
                "examples": ["Take the brass lamp."],
            },
        },
    )

    grammar = envelope.metadata["grammar"]
    assert isinstance(grammar, GrammarHint)
    assert grammar.verbs[0].verb == "take"
    assert grammar.nouns[0].piece_ids == ["lamp"]
    assert envelope.to_dto()["metadata"]["grammar"]["examples"] == [
        "Take the brass lamp."
    ]


def test_runtime_envelope_rejects_invalid_grammar_metadata() -> None:
    with pytest.raises(ValidationError):
        RuntimeEnvelope(
            fragments=[],
            metadata={"grammar": {"verbs": ["take"]}},
        )


def test_command_edge_query_normalizes_and_requires_nonblank_text() -> None:
    assert CommandEdgeQuery(command="  Continue  ").command == "Continue"

    with pytest.raises(ValidationError):
        CommandEdgeQuery(command="   ")


def test_edge_resolution_request_shapes_are_mutually_exclusive() -> None:
    adapter = TypeAdapter(EdgeResolutionRequest)

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "edge_id": str(uuid4()),
                "find_edge": {
                    "kind": "command",
                    "command": "continue",
                },
            }
        )
