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
    grammar = entered.metadata["grammar"]
    assert "Inspect a document" in grammar.examples
    assert all(
        any(document.piece_id in noun.piece_ids for noun in grammar.nouns)
        for document in documents
    )

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


def _service_session() -> tuple[ServiceManager, User, str]:
    persistence = PersistenceManagerFactory.native_in_mem()
    user = User(label="credentials-shift-user")
    persistence.save(user)
    manager = ServiceManager(persistence)
    world = WorldCompiler().compile(WorldBundle.load(_credential_gate_root()))
    manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="credentials_shift",
    )
    return manager, user, world.label


def _flatten(fragments) -> list:
    flat = []
    for fragment in fragments:
        flat.append(fragment)
        if isinstance(fragment, GroupFragment):
            flat.extend(_flatten(list(fragment.content or [])))
    return flat


def _offered(envelope) -> list[ChoiceFragment]:
    return [
        fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, ChoiceFragment) and fragment.available
    ]


def _commit(manager, user, envelope, text, payload=None):
    choice = next(fragment for fragment in _offered(envelope) if fragment.text == text)
    return manager.resolve_choice(
        user_id=user.uid,
        request=DirectEdgeRequest(edge_id=choice.edge_id, payload=payload),
    )


def _live_graph_edges(persistence, user) -> set:
    ledger = persistence.load(user.current_ledger_id)
    assert isinstance(ledger, Ledger)
    return {edge.uid for edge in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))}


def test_consecutive_credential_turns_offer_no_retired_edge() -> None:
    """Every offered choice must still exist as an open edge in the graph.

    A re-entrant block re-offers on each turn. Before #436, consumed offers were
    never retired from the update window, so the second turn republished the
    first turn's spent choice as available -- and committing it raised
    ``Choice edge not found`` in every port, the CLI floor included.
    """

    manager, user, _ = _service_session()
    persistence = manager.persistence

    envelope = _commit(manager, user, manager.get_story_update(user_id=user.uid),
                       "Work the scheduled shift")
    # Turn one: the block has just been entered and offers its first move.
    assert {fragment.edge_id for fragment in _offered(envelope)} == _live_graph_edges(
        persistence, user
    )

    packet_document = next(
        fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, PieceFragment) and fragment.zone_ref is not None
    )
    envelope = _commit(manager, user, envelope, "Inspect a document",
                       {"piece_ids": [packet_document.piece_id]})

    # Turn two: the block re-offers. The spent inspect edge is gone from the
    # graph, so it must be gone from the rendered list as well.
    offered = {fragment.edge_id for fragment in _offered(envelope)}
    live = _live_graph_edges(persistence, user)
    assert offered == live
    assert len(offered) > 1, "the re-entrant block should now offer its rulings"


def test_credential_gate_shift_completes_through_the_service() -> None:
    """The world reaches a terminal state through the service envelope.

    Complements the graph-level checks above: the shift was always finishable as
    graph edges, and this asserts it is finishable as rendered choices too.
    """

    rulings = {
        "Tomas Vey": "Choose pass",
        "Edda Marrow": "Choose deny",
        "Goran Siv": "Choose arrest",
    }
    manager, user, _ = _service_session()
    envelope = _commit(manager, user, manager.get_story_update(user_id=user.uid),
                       "Work the scheduled shift")

    inspected: set[str] = set()
    for _ in range(40):
        offered = _offered(envelope)
        if not offered:
            break
        pieces = [
            fragment
            for fragment in _flatten(envelope.fragments)
            if isinstance(fragment, PieceFragment)
        ]
        candidate = next(
            (piece.content for piece in pieces if piece.piece_kind == "candidate"), None
        )
        pending = [
            piece
            for piece in pieces
            if piece.zone_ref is not None and piece.piece_id not in inspected
        ]
        offered_text = {fragment.text for fragment in offered}
        if pending and "Inspect a document" in offered_text:
            inspected.add(pending[0].piece_id)
            envelope = _commit(manager, user, envelope, "Inspect a document",
                               {"piece_ids": [pending[0].piece_id]})
            continue
        ruling = rulings.get(candidate)
        assert ruling in offered_text, f"no ruling available for {candidate!r}"
        envelope = _commit(manager, user, envelope, ruling)
    else:
        raise AssertionError("credential_gate did not reach a terminal state")

    assert inspected, "no document was ever inspected"
    prose = " ".join(
        str(fragment.content)
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, ContentFragment)
    )
    assert "3 of 3 calls correct" in prose
    assert "last traveler clears the counter" in prose


def test_an_inspected_document_is_marked_unavailable_in_place() -> None:
    """A spent document stays the same fragment, in the same packet, and says so.

    The inspect move refuses it (`Document piece is not inspectable`), but a
    `pieces` choice constrained to the packet offers whatever the packet holds.
    Without this the only way a player learns a document is spent is the error
    raised after committing it -- Decision Legibility, widget vocabulary §5.1.

    Identity is asserted on `uid`, not `piece_id`: a replacement fragment
    reusing the same `piece_id` would satisfy a looser lookup while breaking
    every control reference pointing at the original.
    """

    manager, user, _ = _service_session()
    envelope = _commit(manager, user, manager.get_story_update(user_id=user.uid),
                       "Work the scheduled shift")
    packet = next(
        fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, GroupFragment) and fragment.zone_role == "packet"
    )
    documents = [
        fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, PieceFragment) and fragment.zone_ref is not None
    ]
    assert documents
    assert all(document.available for document in documents), "nothing inspected yet"

    passport = next(
        document
        for document in documents
        if document.presentation_hints.label_text == "passport"
    )
    original_uid = passport.uid

    envelope = _commit(manager, user, envelope, "Inspect a document",
                       {"piece_ids": [passport.piece_id]})

    spent = next(
        fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, PieceFragment) and fragment.uid == original_uid
    )
    assert spent.available is False
    assert spent.unavailable_reason == "already inspected"
    assert spent.piece_id == passport.piece_id
    assert spent.zone_ref == packet.uid, "a spent document stays in the packet"

    restated = next(
        fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, GroupFragment) and fragment.zone_role == "packet"
    )
    assert spent.uid in restated.member_ids, "and stays a member of it"


def test_only_the_inspected_document_of_a_packet_is_marked_spent() -> None:
    """Availability is per document, not per packet.

    The first traveler carries a single document, so a one-document fixture
    cannot tell "this one is spent" apart from "the packet is closed". Edda
    carries three.
    """

    rulings = {"Tomas Vey": "Choose pass"}
    manager, user, _ = _service_session()
    envelope = _commit(manager, user, manager.get_story_update(user_id=user.uid),
                       "Work the scheduled shift")

    # Clear the first traveler to reach one with several documents.
    for _ in range(6):
        pieces = [
            fragment
            for fragment in _flatten(envelope.fragments)
            if isinstance(fragment, PieceFragment)
        ]
        candidate = next(
            (piece.content for piece in pieces if piece.piece_kind == "candidate"), None
        )
        documents = [piece for piece in pieces if piece.zone_ref is not None]
        if len(documents) > 1:
            break
        offered = {fragment.text for fragment in _offered(envelope)}
        ruling = rulings.get(candidate)
        if ruling in offered:
            envelope = _commit(manager, user, envelope, ruling)
        elif "Inspect a document" in offered:
            live = next(document for document in documents if document.available)
            envelope = _commit(manager, user, envelope, "Inspect a document",
                               {"piece_ids": [live.piece_id]})
        else:
            break
    else:
        raise AssertionError("never reached a multi-document packet")

    assert len(documents) > 1
    target = next(document for document in documents if document.available)
    envelope = _commit(manager, user, envelope, "Inspect a document",
                       {"piece_ids": [target.piece_id]})

    after = {
        fragment.uid: fragment
        for fragment in _flatten(envelope.fragments)
        if isinstance(fragment, PieceFragment)
    }
    assert after[target.uid].available is False
    siblings = [
        after[document.uid]
        for document in documents
        if document.uid != target.uid and document.uid in after
    ]
    assert siblings, "the other documents must still be projected"
    assert all(sibling.available for sibling in siblings), (
        "inspecting one document must not close the rest of the packet"
    )
