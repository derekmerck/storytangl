"""Tests for credentials' structured fragment emission (Bridge.1).

Verifies that the handler projects candidate / packet-zone / document pieces and
finding KvFragments alongside the prose fallback, with stable uids for in-place
update across rounds.
"""

from __future__ import annotations

from tangl.core import Graph
from tangl.journal.fragments import (
    ContentFragment,
    GroupFragment,
    KvFragment,
    PieceFragment,
)
from tangl.mechanics.credentials import CredentialToken, Indication
from tangl.mechanics.games import (
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
    HasGame,
)
from tangl.story import Block
from tangl.vm import Frame, VmPhaseCtx
from engine.tests.mechanics.games.credentials_helpers import make_credential_case as CredentialCase


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


def _renderable_case() -> CredentialCase:
    return CredentialCase(
        candidate_name="Edda Marrow",
        presented_documents={"passport": "A worn passport."},
        id_card=CredentialToken(indication=Indication.TRAVEL),
    )


def _game(*cases: CredentialCase) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(roster=list(cases) or [_case()])
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


class _CredentialsBlock(HasGame, Block):
    _game_class = CredentialsGame
    _game_handler_class = CredentialsGameHandler


def _live_game(
    *cases: CredentialCase,
) -> tuple[_CredentialsBlock, CredentialsGameHandler, VmPhaseCtx]:
    graph = Graph(label="credential-journal")
    block = graph.add_node(
        kind=_CredentialsBlock,
        label="checkpoint",
        game_state=CredentialsGame(roster=list(cases) or [_case()]),
    )
    handler = block.game_handler
    handler.setup(block.game)
    return block, handler, Frame(graph=graph, cursor=block)._make_ctx()


def _by_type(fragments, kind):
    return [f for f in fragments if isinstance(f, kind)]


class TestStructuredEmission:
    def test_initial_arrival_precedes_the_structured_packet_surface(self) -> None:
        block, handler, ctx = _live_game(_renderable_case())

        fragments = handler.get_journal_fragments(block.game, ctx=ctx)
        content = _by_type(fragments, ContentFragment)
        candidate = next(
            fragment
            for fragment in fragments
            if isinstance(fragment, PieceFragment) and fragment.piece_kind == "candidate"
        )

        assert len(content) == 2
        assert "Edda Marrow" in content[0].content
        assert "identity document" in content[1].content
        assert content[0].source_id == block.game.active_case.packet_manager.bearer_id
        assert content[1].source_id == block.uid
        assert fragments.index(content[0]) < fragments.index(content[1]) < fragments.index(candidate)
        assert not any(
            leaked in " ".join(fragment.content for fragment in content).lower()
            for leaked in ("mismatch", "invalid", "arrest", "deny", "forged")
        )

    def test_same_candidate_moves_do_not_repeat_arrival_narration(self) -> None:
        block, handler, ctx = _live_game(_renderable_case())
        handler.receive_move(block.game, ("inspect", "passport"))

        content = _by_type(handler.get_journal_fragments(block.game, ctx=ctx), ContentFragment)

        assert all("steps forward" not in fragment.content for fragment in content)
        assert all("present their documents" not in fragment.content for fragment in content)

    def test_decision_introduces_exactly_one_next_candidate_after_its_outcome(self) -> None:
        block, handler, ctx = _live_game(_case(), CredentialCase(candidate_name="Tomas Vey"))
        handler.receive_move(block.game, ("decide", "deny"))

        fragments = handler.get_journal_fragments(block.game, ctx=ctx)
        content = _by_type(fragments, ContentFragment)
        candidate = next(
            fragment
            for fragment in fragments
            if isinstance(fragment, PieceFragment) and fragment.piece_kind == "candidate"
        )

        assert "You choose" in content[0].content
        assert sum("steps forward" in fragment.content for fragment in content) == 1
        assert sum("present their documents" in fragment.content for fragment in content) == 1
        assert "Tomas Vey" in content[2].content
        assert fragments.index(content[2]) < fragments.index(candidate)

    def test_final_decision_does_not_introduce_a_new_candidate(self) -> None:
        block, handler, ctx = _live_game()
        handler.receive_move(block.game, ("decide", "deny"))

        content = _by_type(handler.get_journal_fragments(block.game, ctx=ctx), ContentFragment)

        assert all("steps forward" not in fragment.content for fragment in content)
        assert all("present their documents" not in fragment.content for fragment in content)

    def test_profile_can_replace_arrival_wording_with_the_same_bindings(self) -> None:
        block, handler, ctx = _live_game(_renderable_case())
        block.game.presentation.candidate_arrival_template = (
            "Hall monitor meets {{ candidate_name }}: "
            "{{ render_as(candidate, 'presence_description') }}"
        )
        block.game.presentation.packet_presentation_template = (
            "Student papers: {{ render_as(packet, 'inspection_description') }}"
        )

        content = _by_type(handler.get_journal_fragments(block.game, ctx=ctx), ContentFragment)

        assert content[0].content.startswith("Hall monitor meets Edda Marrow")
        assert content[1].content.startswith("Student papers: identity document")

    def test_initial_projection_emits_candidate_packet_and_documents(self) -> None:
        game, handler = _game()

        frags = handler.get_journal_fragments(game)

        assert any(
            isinstance(fragment, PieceFragment) and fragment.piece_kind == "candidate"
            for fragment in frags
        )
        assert any(
            isinstance(fragment, GroupFragment) and fragment.zone_role == "packet"
            for fragment in frags
        )
        assert not _by_type(frags, ContentFragment)

    def test_inspect_emits_candidate_packet_and_documents(self) -> None:
        game, handler = _game()
        handler.receive_move(game, ("inspect", "passport"))
        frags = handler.get_journal_fragments(game)

        pieces = _by_type(frags, PieceFragment)
        candidate = [p for p in pieces if p.piece_kind == "candidate"]
        docs = [p for p in pieces if p.piece_kind != "candidate"]

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
        first = [
            p
            for p in _by_type(handler.get_journal_fragments(game), PieceFragment)
            if p.piece_kind == "candidate"
        ][0]

        handler.receive_move(game, ("inspect", "work permit"))
        second = [
            p
            for p in _by_type(handler.get_journal_fragments(game), PieceFragment)
            if p.piece_kind == "candidate"
        ][0]

        assert first.uid == second.uid  # same candidate -> in-place update

    def test_distinct_games_get_distinct_piece_uids(self) -> None:
        # Two credentials games (e.g. a scheduled + a randomized shift) must not
        # collide on a shared global fragment uid in the client registry.
        game_a, handler_a = _game()
        game_b, handler_b = _game()
        handler_a.receive_move(game_a, ("inspect", "passport"))
        handler_b.receive_move(game_b, ("inspect", "passport"))

        def candidate_uid(handler, game):
            return [
                p for p in _by_type(handler.get_journal_fragments(game), PieceFragment)
                if p.piece_kind == "candidate"
            ][0].uid

        assert candidate_uid(handler_a, game_a) != candidate_uid(handler_b, game_b)

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
        candidate = [
            p for p in _by_type(frags, PieceFragment) if p.piece_kind == "candidate"
        ]
        assert candidate and candidate[0].content == "Tomas Vey"
