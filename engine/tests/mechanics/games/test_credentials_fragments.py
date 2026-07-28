"""Tests for credentials' structured fragment emission (Bridge.1).

Verifies that the handler projects candidate / packet-zone / document pieces and
finding KvFragments alongside the prose fallback, with stable uids for in-place
update across rounds.
"""

from __future__ import annotations

from tangl.core import Graph, Selector
from tangl.journal.fragments import (
    ContentFragment,
    GroupFragment,
    KvFragment,
    PieceFragment,
)
from tangl.mechanics.credentials import CredentialStatus, CredentialToken, Indication
from tangl.mechanics.games import (
    CredentialDisposition,
    CredentialPresentationProfile,
    CredentialsGame,
    CredentialsGameHandler,
    HasGame,
)
from tangl.mechanics.presence.look import HairColor, HairStyle, Look, SkinTone
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
        assert "A worn passport." in content[1].content
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

    def test_component_documents_share_ordered_content_with_packet_prose(self) -> None:
        case = CredentialCase(
            candidate_name="Edda Marrow",
            presented_documents={
                "passport": "A blue passport.",
                "travel permit": "A blue travel permit.",
                "work permit": "A blue work permit.",
                "baggage": "A blue suitcase.",
            },
            id_card=CredentialToken(indication=Indication.TRAVEL),
            packet=[
                CredentialToken(indication=Indication.TRAVEL),
                CredentialToken(indication=Indication.WORK),
            ],
        )
        block, handler, ctx = _live_game(case)

        fragments = handler.get_journal_fragments(block.game, ctx=ctx)
        packet_prose = _by_type(fragments, ContentFragment)[1].content
        documents = [
            fragment
            for fragment in _by_type(fragments, PieceFragment)
            if fragment.piece_kind != "candidate"
        ]
        component_pieces = [
            fragment for fragment in documents if "component_id" in fragment.properties
        ]
        packet_components = block.game.active_case.packet_manager.document_components()

        assert [piece.properties["component_id"] for piece in component_pieces] == [
            component.uid for component in packet_components
        ]
        assert [piece.content for piece in component_pieces] == [
            "A blue passport.",
            "A blue travel permit.",
            "A blue work permit.",
        ]
        assert [packet_prose.index(piece.content) for piece in component_pieces] == sorted(
            packet_prose.index(piece.content) for piece in component_pieces
        )
        baggage = next(piece for piece in documents if piece.content == "A blue suitcase.")
        assert "component_id" not in baggage.properties

    def test_default_identity_projection_uses_the_same_recursive_portrait_text(self) -> None:
        case = CredentialCase(
            candidate_name="Edda Marrow",
            presented_documents={"baggage": "A lacquered case."},
            id_card=CredentialToken(indication=Indication.TRAVEL),
        )
        block, handler, ctx = _live_game(case)
        packet = block.game.active_case.packet_manager
        packet.resolve_subject(packet.bearer_id).look = Look(
            hair_color=HairColor.RED,
            hair_style=HairStyle.LONG,
            skin_tone=SkinTone.OLIVE,
        )

        fragments = handler.get_journal_fragments(block.game, ctx=ctx)
        packet_prose = _by_type(fragments, ContentFragment)[1].content
        identity_piece = next(
            piece
            for piece in _by_type(fragments, PieceFragment)
            if piece.properties.get("component_id")
            == packet.document_components()[0].uid
        )

        assert "red long hair" in identity_piece.content
        assert identity_piece.content in packet_prose
        assert identity_piece.properties["look_description"] in identity_piece.content

    def test_procedural_default_identity_description_falls_through_to_portrait(self) -> None:
        case = CredentialCase(
            candidate_name="Edda Marrow",
            id_card=CredentialToken(indication=Indication.TRAVEL),
        )
        profile = CredentialPresentationProfile()
        profile.render_case(case, [])
        assert case.presented_documents[profile.identity_label] == profile.identity_description

        block, handler, ctx = _live_game(case)
        packet = block.game.active_case.packet_manager
        packet.resolve_subject(packet.bearer_id).look = Look(
            hair_color=HairColor.RED,
            hair_style=HairStyle.LONG,
            skin_tone=SkinTone.OLIVE,
        )

        fragments = handler.get_journal_fragments(block.game, ctx=ctx)
        packet_prose = _by_type(fragments, ContentFragment)[1].content
        identity_piece = next(
            piece
            for piece in _by_type(fragments, PieceFragment)
            if piece.presentation_hints.label_text == profile.identity_label
        )

        assert "red long hair" in identity_piece.content
        assert identity_piece.content in packet_prose

    def test_duplicate_component_labels_have_distinct_fragment_uids(self) -> None:
        case = CredentialCase(
            presented_documents={"travel permit": "A stamped travel permit."},
            packet=[
                CredentialToken(indication=Indication.TRAVEL),
                CredentialToken(indication=Indication.TRAVEL),
            ],
        )
        block, handler, ctx = _live_game(case)

        fragments = handler.get_journal_fragments(block.game, ctx=ctx)
        packet = next(
            fragment
            for fragment in fragments
            if isinstance(fragment, GroupFragment) and fragment.zone_role == "packet"
        )
        permits = [
            piece
            for piece in _by_type(fragments, PieceFragment)
            if piece.presentation_hints.label_text == "travel permit"
        ]

        assert len(permits) == 2
        assert len({piece.uid for piece in permits}) == 2
        assert len(set(packet.member_ids)) == 2
        assert {piece.piece_id for piece in permits} == {"0:travel permit"}

    def test_invalid_components_do_not_change_the_visible_piece_shape(self) -> None:
        valid = CredentialCase(
            presented_documents={"passport": "A passport."},
            id_card=CredentialToken(indication=Indication.TRAVEL),
        )
        invalid = CredentialCase(
            presented_documents={"passport": "A passport."},
            id_card=CredentialToken(
                indication=Indication.TRAVEL,
                status=CredentialStatus.FORGED,
            ),
        )
        valid_block, valid_handler, valid_ctx = _live_game(valid)
        invalid_block, invalid_handler, invalid_ctx = _live_game(invalid)

        def visible_shape(handler, game, ctx):
            fragments = handler.get_journal_fragments(game, ctx=ctx)
            pieces = [
                piece
                for piece in _by_type(fragments, PieceFragment)
                if piece.piece_kind != "candidate"
            ]
            return [
                (
                    piece.piece_kind,
                    piece.presentation_hints.label_text,
                    set(piece.properties),
                )
                for piece in pieces
            ], " ".join(
                fragment.content for fragment in _by_type(fragments, ContentFragment)
            ).lower()

        valid_shape, valid_text = visible_shape(valid_handler, valid_block.game, valid_ctx)
        invalid_shape, invalid_text = visible_shape(
            invalid_handler,
            invalid_block.game,
            invalid_ctx,
        )

        assert invalid_shape == valid_shape
        assert not any(
            term in valid_text + invalid_text
            for term in ("forged", "invalid", "deny")
        )

    def test_unbound_projection_keeps_authored_document_text(self) -> None:
        case = CredentialCase(
            presented_documents={"passport": "A stamped passport."},
            id_card=CredentialToken(indication=Indication.TRAVEL),
        )
        game, handler = _game(case)

        pieces = [
            piece
            for piece in _by_type(handler.get_journal_fragments(game), PieceFragment)
            if piece.piece_kind != "candidate"
        ]

        assert len(pieces) == 1
        assert pieces[0].content == "A stamped passport."
        assert (
            pieces[0].properties["component_id"]
            == game.active_case.packet_manager.document_components()[0].uid
        )

    def test_component_piece_projection_survives_graph_roundtrip(self) -> None:
        case = CredentialCase(
            presented_documents={
                "passport": "A stamped passport.",
                "travel permit": "A stamped travel permit.",
            },
            id_card=CredentialToken(indication=Indication.TRAVEL),
            packet=[CredentialToken(indication=Indication.TRAVEL)],
        )
        block, handler, ctx = _live_game(case)

        def component_projection(active_handler, game, active_ctx):
            return [
                (piece.content, piece.properties["component_id"])
                for piece in _by_type(
                    active_handler.get_journal_fragments(game, ctx=active_ctx),
                    PieceFragment,
                )
                if "component_id" in piece.properties
            ]

        before = component_projection(handler, block.game, ctx)
        restored_graph = Graph.structure(ctx.graph.unstructure())
        restored_block = restored_graph.find_one(Selector(label="checkpoint"))
        restored_handler = restored_block.game_handler
        restored_ctx = Frame(graph=restored_graph, cursor=restored_block)._make_ctx()

        assert component_projection(restored_handler, restored_block.game, restored_ctx) == before
