"""Portable wire fixtures through the shipped headless pygame adapter."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from tangl.core import BaseFragment
from tangl.journal.fragments import fragment_from_dto
from tangl.pygame_client.bridge import (
    PygameSessionBridge,
    UnsupportedAccepts,
    commit_payload,
    selectable_pieces,
)
from tangl.service import JsonValue


FIXTURES = Path(__file__).resolve().parents[3] / "engine/contrib/conformance/fixtures"


def _fixture(name: str) -> list[BaseFragment]:
    wire = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return [fragment_from_dto(fragment) for fragment in wire["fragments"]]


def test_crossroads_narration_choices_and_status_survive() -> None:
    bridge = PygameSessionBridge()
    fragments = _fixture("crossroads_inn")
    (turn,) = bridge.build_turns(fragments)
    expected_lines = [
        (None, "Rain drums on the thatch. Inside the Crossroads Inn the air is smoke and peat."),
        ("Stranger", "They say you're headed north."),
    ]
    assert [(line.speaker, line.text) for line in turn.lines] == expected_lines
    assert [(line.speaker, line.text) for block in bridge.build_passages(fragments)
            for passage in block for line in passage.lines] == expected_lines
    assert [(choice.text, str(choice.edge_id), choice.available, choice.unavailable_reason)
            for choice in turn.choices] == [
        ("Pay the forty silver.", "00000000-0000-4000-8000-000000001108", True, None),
        ("Lift the map while he drinks.", "00000000-0000-4000-8000-000000001109", False,
         "Sleight of Hand 1, need 2."),
    ]
    assert [(row.key, row.value) for row in turn.findings] == [
        ("time", "late evening"), ("coin", "63 s"), ("weather", "rain"),
    ]


def test_credentials_packet_selection_and_pick() -> None:
    (turn,) = PygameSessionBridge().build_turns(_fixture("credentials_shift"))
    assert [line.text for line in turn.lines] == [
        "You unfold the work permit. The seal is sound, but the date stamp shows expiry months past."
    ]
    zone_id = UUID("00000000-0000-4000-8000-000000000604")
    assert [(zone.uid, zone.role, zone.label) for zone in turn.zones] == [
        (zone_id, "packet", "Credentials packet")
    ]
    assert [(piece.piece_id, piece.kind, piece.zone_ref) for piece in turn.pieces] == [
        ("candidate-0", "candidate", None),
        ("0:passport", "id_card", zone_id),
        ("0:work permit", "permit", zone_id),
    ]
    assert [(row.key, row.value, row.emphasis) for row in turn.findings] == [
        ("work permit", "The permit's issue stamp has expired.", "warn"),
        ("packet consistency", "An expired permit does not satisfy the work rule.", "danger"),
    ]
    assert [(choice.text, str(choice.edge_id), choice.accepts.kind) for choice in turn.choices] == [
        ("Inspect a document.", "00000000-0000-4000-8000-0000000006e0", "pieces"),
        ("Choose pass.", "00000000-0000-4000-8000-0000000006e1", "pick"),
        ("Choose deny.", "00000000-0000-4000-8000-0000000006e2", "pick"),
        ("Request reissue of work permit.", "00000000-0000-4000-8000-0000000006e3", "pick"),
        ("Verify identity.", "00000000-0000-4000-8000-0000000006e4", "pick"),
        ("Request search.", "00000000-0000-4000-8000-0000000006e5", "pick"),
    ]
    assert all(choice.available for choice in turn.choices)
    inspect = turn.choices[0]
    assert (inspect.accepts.min, inspect.accepts.max) == (1, 1)
    assert inspect.accepts.constraints.target_zone_ref == zone_id
    assert [piece.piece_id for piece in selectable_pieces(turn, inspect)] == [
        "0:passport", "0:work permit"
    ]
    assert (inspect.edge_id, commit_payload(inspect, ["0:work permit"])) == (
        UUID("00000000-0000-4000-8000-0000000006e0"), {"piece_ids": ["0:work permit"]},
    )
    with pytest.raises(UnsupportedAccepts, match="at least 1"):
        commit_payload(inspect)
    with pytest.raises(UnsupportedAccepts, match="at most 1"):
        commit_payload(inspect, ["0:passport", "0:work permit"])
    assert (turn.choices[1].edge_id, commit_payload(turn.choices[1])) == (
        UUID("00000000-0000-4000-8000-0000000006e1"), {},
    )


def test_decoded_pick_keeps_authored_activation_payload() -> None:
    fragment = fragment_from_dto({
        "fragment_type": "choice", "edge_id": "00000000-0000-4000-8000-0000000006ff",
        "text": "Choose", "accepts": {"kind": "pick"}, "payload": {"verdict": "pass"},
    })
    (choice,) = PygameSessionBridge().build_turns([fragment])[0].choices
    assert (choice.edge_id, commit_payload(choice)) == (
        UUID("00000000-0000-4000-8000-0000000006ff"), {"verdict": "pass"},
    )


def test_fixture_piece_selection_reaches_pygame_commit() -> None:
    pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")
    from tangl.pygame_client.__main__ import _commit_pending
    from tangl.pygame_client.models import PendingSelection
    from tangl.pygame_client.stage import choice_action

    (turn,) = PygameSessionBridge().build_turns(_fixture("credentials_shift"))
    choice = turn.choices[0]
    selectable = selectable_pieces(turn, choice)
    assert [piece.piece_id for piece in selectable] == ["0:passport", "0:work permit"]
    assert choice_action(choice).choice == choice
    received: list[tuple[UUID, JsonValue]] = []

    class RecordingBridge:
        def choose(self, edge_id: UUID, payload: JsonValue) -> None:
            received.append((edge_id, payload))

    _commit_pending(
        RecordingBridge(), PendingSelection(choice=choice, picked=[selectable[1].piece_id]),
    )
    assert received == [
        (UUID("00000000-0000-4000-8000-0000000006e0"), {"piece_ids": ["0:work permit"]})
    ]


def test_quantity_is_readable_but_explicitly_refused() -> None:
    (turn,) = PygameSessionBridge().build_turns(_fixture("quantity_payload"))
    assert [line.text for line in turn.lines] == [
        "The quartermaster taps the crate. Rations are two coin each."
    ]
    assert [(row.key, row.value) for row in turn.findings] == [("wallet", "7 coin"), ("rations", "0")]
    (choice,) = turn.choices
    assert choice.available
    assert (choice.text, choice.edge_id, choice.accepts.kind) == (
        "Buy rations.", UUID("00000000-0000-4000-8000-000000001404"), "quantity",
    )
    assert (choice.accepts.min, choice.accepts.max, choice.accepts.step, choice.accepts.unit) == (
        1, 3, 1, "ration",
    )
    with pytest.raises(UnsupportedAccepts, match="quantity"):
        commit_payload(choice)


def test_compose_is_readable_but_explicitly_refused() -> None:
    (turn,) = PygameSessionBridge().build_turns(_fixture("compose_payload"))
    assert [line.text for line in turn.lines] == ["The guard waits by the gate, palm open."]
    zone_id = UUID("00000000-0000-4000-8000-000000000803")
    assert [(zone.uid, zone.role) for zone in turn.zones] == [(zone_id, "field")]
    assert [(piece.piece_id, piece.text, piece.zone_ref) for piece in turn.pieces] == [
        ("guard", "gate guard", zone_id)
    ]
    (choice,) = turn.choices
    assert choice.available
    assert (choice.text, choice.edge_id, choice.accepts.kind) == (
        "Give coins.", UUID("00000000-0000-4000-8000-000000001805"), "compose",
    )
    assert [(part.role, part.accepts.kind) for part in choice.accepts.parts] == [
        ("amount", "quantity"), ("target", "pieces"),
    ]
    assert choice.accepts.parts[1].accepts.constraints.target_zone_ref == zone_id
    with pytest.raises(UnsupportedAccepts, match="compose"):
        commit_payload(choice)
