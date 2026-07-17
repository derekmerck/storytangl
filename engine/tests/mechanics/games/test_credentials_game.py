"""Tests for the credential checkpoint-shift mechanic."""

from __future__ import annotations

import pytest

from tangl.core import Graph
from tangl.mechanics.credentials import materialize_packet
from tangl.mechanics.games import (
    CredentialStatus,
    CredentialToken,
    GameResult,
    HasGame,
    Indication,
    Region,
)
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.mechanics.games.handlers import inject_game_context
from tangl.story import Action, Block
from tangl.vm import Ledger, TraversableEdge as ChoiceEdge


def _two_case_roster() -> list[CredentialCase]:
    """A deny-then-pass shift, with case 0 carrying an extra 'baggage' document."""

    return [
        CredentialCase(
            candidate_name="Edda Marrow",
            presented_documents={
                "passport": "A worn passport with a blurred seal.",
                "travel permit": "A permit stamped for this week.",
                "baggage": "A lacquered case with a stubborn clasp.",
            },
            hidden_facts={"passport": "The seal impression is wrong for this border."},
            packet_hidden_facts={
                "packet consistency": "The documents do not satisfy the rules.",
            },
            correct_disposition=CredentialDisposition.DENY,
        ),
        CredentialCase(
            candidate_name="Tomas Vey",
            presented_documents={
                "passport": "A crisp passport, seal sharp and current.",
                "travel permit": "A permit stamped for this very week.",
            },
            hidden_facts={},
            packet_hidden_facts={},
            correct_disposition=CredentialDisposition.PASS,
        ),
    ]


def _ready_game(**overrides) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(roster=_two_case_roster(), **overrides)
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


class CredentialsBlock(HasGame, Block):
    """Test block embedding the credential shift."""

    _game_class = CredentialsGame
    _game_handler_class = CredentialsGameHandler


class TestCredentialsCore:
    """Core shift behavior without the VM."""

    def test_inspect_reveals_hidden_finding(self) -> None:
        game, handler = _ready_game()

        result = handler.receive_move(game, ("inspect", "passport"))

        assert result.name == "CONTINUE"
        assert "passport" in game.discovered_findings

    def test_packet_review_records_packet_finding(self) -> None:
        game, handler = _ready_game()
        handler.receive_move(game, ("inspect", "passport"))

        result = handler.receive_move(game, ("inspect", "packet consistency"))

        assert result.name == "CONTINUE"
        assert "packet consistency" in game.packet_findings

    def test_document_inspection_is_one_piece_selector_move(self) -> None:
        game, handler = _ready_game()

        inspect_moves = [
            move for move in handler.get_provisioned_moves(game) if move.kind == "inspect"
        ]

        assert len(inspect_moves) == 1
        assert handler.get_move_label(game, inspect_moves[0]) == "Inspect a document"
        accepts = handler.get_move_accepts(game, inspect_moves[0])
        assert accepts.kind == "pieces"
        assert accepts.constraints is not None
        assert accepts.constraints.target_zone_ref

    def test_piece_payload_resolves_to_document_inspection(self) -> None:
        game, handler = _ready_game()
        selector = next(
            move for move in handler.get_provisioned_moves(game) if move.kind == "inspect"
        )

        resolved = handler.resolve_move_payload(
            game,
            selector,
            {"piece_ids": ["0:passport"]},
        )

        assert resolved.kind == "inspect"
        assert resolved.target == "passport"

    def test_stale_document_piece_payload_is_rejected(self) -> None:
        game, handler = _ready_game()
        selector = next(
            move for move in handler.get_provisioned_moves(game) if move.kind == "inspect"
        )
        handler.receive_move(game, ("inspect", "passport"))

        with pytest.raises(ValueError, match="not inspectable"):
            handler.resolve_move_payload(
                game,
                selector,
                {"piece_ids": ["0:passport"]},
            )

    def test_arrest_move_can_be_disabled(self) -> None:
        game, handler = _ready_game(allow_arrest=False)
        handler.receive_move(game, ("inspect", "passport"))

        assert ("decide", "arrest") not in handler.get_available_moves(game)

    def test_correct_disposition_advances_without_terminal(self) -> None:
        game, handler = _ready_game()
        handler.receive_move(game, ("inspect", "passport"))

        result = handler.receive_move(game, ("decide", "deny"))

        assert result.name == "WIN"
        # Game is not over: a second candidate remains.
        assert game.result is GameResult.IN_PROCESS
        assert not game.is_terminal
        assert game.case_index == 1

    def test_advance_resets_only_per_case_state(self) -> None:
        game, handler = _ready_game()
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("inspect", "packet consistency"))
        handler.receive_move(game, ("decide", "deny"))

        # Per-case working state is wiped for the next candidate...
        assert game.inspected_targets == []
        assert game.revealed_findings == {}
        assert game.inspected_packet_targets == []
        assert game.packet_findings == {}
        assert game.committed_decision is None
        assert game.current_stage == "documents"
        # ...but shift-level state persists.
        assert len(game.case_results) == 1
        assert game.case_results[0].candidate_name == "Edda Marrow"
        assert game.case_results[0].correct is True
        assert game.score == {"player": 1, "opponent": 0}

    def test_full_roster_traversal_wins(self) -> None:
        game, handler = _ready_game()

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "deny"))
        assert not game.is_terminal  # terminal only after the final case

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "pass"))

        assert game.shift_complete is True
        assert game.is_terminal
        assert game.result is GameResult.WIN
        assert game.correct_count == 2
        assert [r.correct for r in game.case_results] == [True, True]

    def test_one_wrong_call_fails_shift_under_strict_default(self) -> None:
        game, handler = _ready_game()

        # Wrong call on the first candidate (pass instead of deny).
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "pass"))
        # Correct call on the second.
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "pass"))

        assert game.is_terminal
        assert game.result is GameResult.LOSE
        assert game.correct_count == 1

    def test_penalty_threshold_allows_a_miss(self) -> None:
        # Edda should DENY; passing her is one step off (penalty 2). A threshold
        # of 2 tolerates exactly that.
        game, handler = _ready_game(penalty_threshold=2)

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "pass"))  # wrong (deny expected) -> +2
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "pass"))  # correct -> +0

        assert game.total_penalty == 2
        assert game.result is GameResult.WIN
        assert game.correct_count == 1

    def test_arrest_when_wrong_is_a_grave_penalty(self) -> None:
        # Arresting Edda (should DENY) is two steps off -> penalty 5, over the
        # strict default threshold of 0.
        game, handler = _ready_game()  # penalty_threshold defaults to 0
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "arrest"))  # deny expected -> +5

        assert game.case_results[0].penalty == 5
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "pass"))  # Tomas correct
        assert game.total_penalty == 5
        assert game.result is GameResult.LOSE

    def test_terminal_routing_only_after_final_case(self) -> None:
        game, handler = _ready_game()
        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "deny"))

        # Mid-shift: still in process, awaiting the next candidate.
        assert game.result is GameResult.IN_PROCESS
        assert game.is_ready

    def test_expected_disposition_context_seams(self) -> None:
        game = CredentialsGame(
            roster=[
                CredentialCase(correct_disposition=CredentialDisposition.PASS, blacklist=True),
                CredentialCase(correct_disposition=CredentialDisposition.DENY, whitelist=True),
            ]
        )

        assert game.expected_disposition(game.roster[0]) is CredentialDisposition.ARREST
        assert game.expected_disposition(game.roster[1]) is CredentialDisposition.PASS

    def test_namespace_exposes_shift_progress(self) -> None:
        game, handler = _ready_game()

        opening = game.to_namespace()
        assert opening["credential_roster_size"] == 2
        assert opening["credential_case_number"] == 1
        assert opening["credential_cases_remaining"] == 2
        assert opening["credential_correct_count"] == 0
        assert opening["credential_shift_complete"] is False
        # Correct/incorrect counts come from the base game's player/opponent score
        # (no credentials-specific duplicate of it).
        assert opening["player_score"] == 0
        assert opening["opponent_score"] == 0

        handler.receive_move(game, ("inspect", "passport"))
        handler.receive_move(game, ("decide", "deny"))  # first case is a correct deny

        mid = game.to_namespace()
        assert mid["credential_case_number"] == 2
        assert mid["credential_cases_remaining"] == 1
        assert mid["credential_correct_count"] == 1
        assert mid["player_score"] == 1
        assert mid["credential_candidate_name"] == "Tomas Vey"


class TestCredentialsIntegration:
    """VM and HasGame integration across a full roster."""

    def _actions(self, ledger: Ledger) -> list[Action]:
        return [a for a in ledger.cursor.edges_out() if isinstance(a, Action)]

    def _labels(self, ledger: Ledger) -> set[str]:
        return {a.label for a in self._actions(ledger)}

    def _choose(
        self,
        ledger: Ledger,
        label: str,
        *,
        choice_payload: dict[str, object] | None = None,
    ) -> None:
        action = next(a for a in self._actions(ledger) if a.label == label)
        ledger.resolve_choice(action.uid, choice_payload=choice_payload)

    def _inspect(self, ledger: Ledger, target: str) -> None:
        game = ledger.cursor.game
        self._choose(
            ledger,
            "Inspect a document",
            choice_payload={"piece_ids": [f"{game.case_index}:{target}"]},
        )

    def test_walk_full_roster_to_victory(self) -> None:
        graph = Graph(label="credential_shift")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = CredentialsBlock.create_game_block(
            graph=graph,
            game_class=CredentialsGame,
            handler_class=CredentialsGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="checkpoint",
        )
        block.game.roster = _two_case_roster()
        block.game_handler.setup(block.game)

        intro_to_checkpoint = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Open the gate ledger",
        )
        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_checkpoint.uid)

        # Candidate 1 (Edda) -> deny.
        self._inspect(ledger, "passport")
        self._choose(ledger, "Choose deny")

        # Stale move cleanup: the desk now shows candidate 2's documents only.
        labels = self._labels(ledger)
        assert "Inspect a document" in labels
        assert "Inspect baggage" not in labels  # belonged to candidate 1
        assert not any(label.startswith("Choose ") for label in labels)  # must inspect first
        assert ledger.cursor_id == block.uid  # still mid-shift

        # Candidate 2 (Tomas) -> pass, completing the shift.
        self._inspect(ledger, "passport")
        self._choose(ledger, "Choose pass")

        assert ledger.cursor_id == victory.uid
        content = " ".join(
            f.content
            for f in ledger.get_journal()
            if isinstance(f.content, str)
        )
        assert "shift complete" in content.lower()

    def test_context_exports_discovered_findings(self) -> None:
        graph = Graph(label="credential_context")
        block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
        block.game.roster = _two_case_roster()
        block.game_handler.setup(block.game)
        block.game_handler.receive_move(block.game, ("inspect", "passport"))

        frame = Ledger.from_graph(graph=graph, entry_id=block.uid).get_frame()
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["credential_num_findings"] == 1
        assert "passport" in namespace["credential_discovered_findings"]
        assert namespace["credential_stage"] == "packet"
        assert namespace["credential_roster_size"] == 2

    def test_faceted_request_document_uses_existing_has_game_update_path(self) -> None:
        graph = Graph(label="credential_facets")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")
        block = CredentialsBlock.create_game_block(
            graph=graph,
            game_class=CredentialsGame,
            handler_class=CredentialsGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="checkpoint",
        )
        block.game.roster = [
            CredentialCase(
                packet_manager=materialize_packet(
                    owner=block,
                    region=Region.LOCAL,
                    purpose=Indication.WORK,
                    id_card=CredentialToken(indication=Indication.TRAVEL),
                    credentials=[
                        CredentialToken(
                            indication=Indication.WORK,
                            status=CredentialStatus.MISSING_SEAL,
                            requires_id=True,
                        ),
                    ],
                    possessions=[],
                    label_prefix="Mara",
                ),
            ),
        ]
        block.game_handler.setup(block.game)
        intro_to_checkpoint = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Open the gate ledger",
        )
        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_checkpoint.uid)

        self._inspect(ledger, "passport")
        action = next(
            action
            for action in self._actions(ledger)
            if action.label == "Request reissue of work permit"
        )
        history_size = len(block.game.history)
        ledger.resolve_choice(action.uid)

        assert len(block.game.history) == history_size + 1
        assert block.game.finding_status == {Indication.WORK.value: "cleared"}
        assert block.game.time_spent == 3
