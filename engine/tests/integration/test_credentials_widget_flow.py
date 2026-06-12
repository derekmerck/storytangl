"""Credentials widget projection through the service runtime envelope."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Selector
from tangl.journal.fragments import (
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    PieceFragment,
)
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.persistence import PersistenceManagerFactory
from tangl.service.response import DirectEdgeRequest
from tangl.service.service_manager import ServiceManager
from tangl.service.user.user import User
from tangl.story import Action, InitMode
from tangl.vm import Ledger


def _credential_gate_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "credential_gate"


def _action(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(
            Selector(has_kind=Action, trigger_phase=None),
        )
        if action.text == text or action.label == text
    )


def test_credentials_packet_reaches_service_envelope_as_typed_widgets() -> None:
    persistence = PersistenceManagerFactory.native_in_mem()
    user = User(label="credentials-widget-user")
    persistence.save(user)
    manager = ServiceManager(persistence)
    world = WorldCompiler().compile(WorldBundle.load(_credential_gate_root()))

    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="credentials_widget_flow",
    )
    ledger = persistence.load(user.current_ledger_id)
    assert isinstance(ledger, Ledger)

    entered = manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(
            edge_id=_action(ledger, "Work the scheduled shift").uid,
        ),
    )

    pieces = [
        fragment for fragment in entered.fragments if isinstance(fragment, PieceFragment)
    ]
    packet = next(
        fragment
        for fragment in entered.fragments
        if isinstance(fragment, GroupFragment) and fragment.zone_role == "packet"
    )
    candidate = next(
        fragment for fragment in pieces if fragment.piece_kind == "candidate"
    )
    documents = [fragment for fragment in pieces if fragment.zone_ref == packet.uid]

    assert candidate.content == "Tomas Vey"
    assert candidate.presentation_hints.label_text == "Tomas Vey"
    assert documents
    assert set(packet.member_ids) == {fragment.uid for fragment in documents}
    assert any(isinstance(fragment, ContentFragment) for fragment in entered.fragments)
    inspect_choice = next(
        fragment
        for fragment in entered.fragments
        if isinstance(fragment, ChoiceFragment) and fragment.text == "Inspect a document"
    )
    assert inspect_choice.edge_id is not None
    assert inspect_choice.accepts is not None
    assert inspect_choice.accepts.kind == "pieces"
    assert inspect_choice.accepts.constraints is not None
    assert inspect_choice.accepts.constraints.target_zone_ref == str(packet.uid)

    dto = entered.to_dto()
    piece_payloads = [
        fragment for fragment in dto["fragments"] if fragment["fragment_type"] == "piece"
    ]
    packet_payload = next(
        fragment
        for fragment in dto["fragments"]
        if fragment["fragment_type"] == "group" and fragment["zone_role"] == "packet"
    )
    inspect_payload = next(
        fragment
        for fragment in dto["fragments"]
        if fragment["fragment_type"] == "choice"
        and fragment["text"] == "Inspect a document"
    )

    assert {fragment["uid"] for fragment in piece_payloads if "zone_ref" in fragment} == set(
        packet_payload["member_ids"],
    )
    assert all(fragment["content"] for fragment in piece_payloads)
    assert all(fragment["hints"]["label_text"] for fragment in piece_payloads)
    assert inspect_payload["accepts"] == {
        "kind": "pieces",
        "min": 1,
        "max": 1,
        "constraints": {"target_zone_ref": packet_payload["uid"]},
    }

    passport = next(
        fragment
        for fragment in documents
        if fragment.presentation_hints.label_text == "passport"
    )
    inspected = manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(
            edge_id=inspect_choice.edge_id,
            payload={"piece_ids": [passport.piece_id]},
        ),
    )

    assert any(
        isinstance(fragment, ContentFragment)
        and "inspect the passport" in str(fragment.content).lower()
        for fragment in inspected.fragments
    )
    persisted = persistence.load(user.current_ledger_id)
    assert isinstance(persisted, Ledger)
    assert persisted.cursor.game.inspected_documents == ["passport"]
