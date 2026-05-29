"""Tests for credentials' structured fragment emission (Bridge.1).

Verifies that the handler projects candidate / packet-zone / document pieces and
finding KvFragments alongside the prose fallback, with stable uids for in-place
update across rounds.
"""

from __future__ import annotations

from tangl.journal.fragments import (
    ContentFragment,
    GroupFragment,
    KvFragment,
    PieceFragment,
)
from tangl.mechanics.games import (
    CredentialCase,
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
)


def _case() -> CredentialCase:
    return CredentialCase(
        candidate_name="Edda Marrow",
        presented_documents={
            "passport": "A worn passport.",
            "work permit": "A permit lacking its seal.",
        },
        hidden_facts={"passport": "The seal impression is wrong for this border."},
        correct_disposition=CredentialDisposition.DENY,
    )


def _game(*cases: CredentialCase) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(roster=list(cases) or [_case()])
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def _by_type(fragments, kind):
    return [f for f in fragments if isinstance(f, kind)]


class TestStructuredEmission:
    def test_inspect_emits_candidate_packet_and_documents(self) -> None:
        game, handler = _game()
        handler.receive_move(game, ("inspect", "passport"))
        frags = handler.get_journal_fragments(game)

        pieces = _by_type(frags, PieceFragment)
        candidate = [p for p in pieces if p.kind == "candidate"]
        docs = [p for p in pieces if p.kind != "candidate"]

        assert candidate and candidate[0].content == "Edda Marrow"
        assert candidate[0].properties["declared_purpose"]  # populated
        assert {p.content for p in docs} == {"A worn passport.", "A permit lacking its seal."}

        groups = _by_type(frags, GroupFragment)
        assert groups and groups[0].group_type == "zone"
        # The packet zone references exactly the document piece uids.
        assert set(groups[0].member_ids) == {p.uid for p in docs}
        # Each document points back at the packet zone.
        assert all(p.zone_ref == groups[0].uid for p in docs)

    def test_revealed_finding_emits_kv_row(self) -> None:
        game, handler = _game()
        handler.receive_move(game, ("inspect", "passport"))
        frags = handler.get_journal_fragments(game)

        kvs = _by_type(frags, KvFragment)
        assert kvs
        rows = kvs[0].content
        assert any(row.key == "passport" and row.emphasis == "warn" for row in rows)

    def test_prose_fallback_preserved(self) -> None:
        game, handler = _game()
        handler.receive_move(game, ("inspect", "passport"))
        frags = handler.get_journal_fragments(game)

        prose = _by_type(frags, ContentFragment)
        assert any("inspect" in str(f.content).lower() for f in prose)

    def test_candidate_uid_is_stable_across_rounds(self) -> None:
        game, handler = _game()
        handler.receive_move(game, ("inspect", "passport"))
        first = [p for p in _by_type(handler.get_journal_fragments(game), PieceFragment) if p.kind == "candidate"][0]

        handler.receive_move(game, ("inspect", "work permit"))
        second = [p for p in _by_type(handler.get_journal_fragments(game), PieceFragment) if p.kind == "candidate"][0]

        assert first.uid == second.uid  # same candidate -> in-place update

    def test_no_structural_pieces_once_shift_complete(self) -> None:
        game, handler = _game(_case())  # single-candidate shift
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "deny"))
        assert game.shift_complete

        frags = handler.get_journal_fragments(game)
        assert not _by_type(frags, PieceFragment)
        prose = _by_type(frags, ContentFragment)
        assert any("shift complete" in str(f.content).lower() for f in prose)

    def test_arriving_candidate_pieces_on_non_final_decision(self) -> None:
        # Two-candidate shift: deciding case 0 advances to case 1, whose pieces
        # arrive alongside the "next traveler" prose.
        game, handler = _game(_case(), CredentialCase(candidate_name="Tomas Vey"))
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "deny"))

        frags = handler.get_journal_fragments(game)
        candidate = [p for p in _by_type(frags, PieceFragment) if p.kind == "candidate"]
        assert candidate and candidate[0].content == "Tomas Vey"
