"""Tests for the fixed-list directed call-response game kernel."""

from __future__ import annotations

import json

import pytest

from tangl.core import Graph, Selector
from tangl.journal.fragments import AttributedFragment
from tangl.mechanics.games import (
    CallResponseGame,
    CallResponseGameHandler,
    CallResponseExchange,
    CallResponsePhrase,
    DominanceMatch,
    GamePhase,
    HasGame,
    RoundResult,
)
from tangl.story import Action, Block
from tangl.vm import Ledger, TraversableEdge


class CallResponseBlock(HasGame, Block):
    """Test story node hosting the pure call-response kernel."""

    _game_class = CallResponseGame
    _game_handler_class = CallResponseGameHandler


def _game(*, player_has_initiative: bool = True) -> CallResponseGame:
    return CallResponseGame(
        phrases={
            "taunt": CallResponsePhrase(text="You fight like a dairy farmer.", roles=["call"]),
            "rebuttal": CallResponsePhrase(text="How appropriate.", roles=["response"]),
            "miss": CallResponsePhrase(text="That is not an answer.", roles=["response"]),
            "both": CallResponsePhrase(text="A practiced phrase.", roles=["call", "response"]),
        },
        player_phrase_ids=["taunt", "rebuttal", "both"],
        opponent_phrase_ids=["taunt", "rebuttal", "miss", "both"],
        schedule=[
            DominanceMatch(
                call_phrase_id="taunt",
                response_phrase_id="rebuttal",
                matched=True,
                source_id="dairy-rebuttal",
            ),
            DominanceMatch(
                call_phrase_id="both",
                response_phrase_id="miss",
                matched=False,
                source_id="explicit-negative",
            ),
        ],
        initial_player_has_initiative=player_has_initiative,
        scoring_n=9,
    )


class TestCallResponseKernel:
    """Pure role, initiative, schedule, and evidence behavior."""

    def test_positive_directed_response_wins_for_the_responder(self) -> None:
        game = _game()
        handler = CallResponseGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, "taunt")

        assert result is RoundResult.LOSE
        assert game.score == {"player": 0, "opponent": 1}
        assert game.player_has_initiative is False
        assert game.history[-1].opponent_move == "rebuttal"
        assert game.history[-1].notes == {
            "call_phrase_id": "taunt",
            "response_phrase_id": "rebuttal",
            "matched": True,
            "match_source_id": "dairy-rebuttal",
            "additional_exposed_phrase_ids": [],
            "initiative_before": True,
            "initiative_after": False,
        }
        assert isinstance(game.last_exchange, CallResponseExchange)

    def test_undeclared_pair_misses_and_preserves_caller_initiative(self) -> None:
        game = _game()
        game.opponent_phrase_ids = ["miss"]
        handler = CallResponseGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, "taunt")

        assert result is RoundResult.WIN
        assert game.score == {"player": 1, "opponent": 0}
        assert game.player_has_initiative is True
        assert game.history[-1].notes["matched"] is False
        assert game.history[-1].notes["match_source_id"] is None

    def test_directed_match_from_opponent_call_flips_initiative_to_player(self) -> None:
        game = _game(player_has_initiative=False)
        game.player_phrase_ids = ["rebuttal"]
        game.opponent_phrase_ids = ["taunt"]
        handler = CallResponseGameHandler()
        handler.setup(game)

        assert game.opponent_next_move == "taunt"
        assert handler.get_available_moves(game) == ["rebuttal"]
        result = handler.receive_move(game, "rebuttal")

        assert result is RoundResult.WIN
        assert game.player_has_initiative is True
        assert game.history[-1].notes["initiative_before"] is False
        assert game.history[-1].notes["initiative_after"] is True

    def test_undeclared_response_to_an_opponent_call_misses(self) -> None:
        game = _game(player_has_initiative=False)
        game.player_phrase_ids = ["miss"]
        game.opponent_phrase_ids = ["taunt"]
        handler = CallResponseGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, "miss")

        assert result is RoundResult.LOSE
        assert game.player_has_initiative is False
        assert game.history[-1].notes["match_source_id"] is None

    def test_role_gating_changes_player_and_opponent_move_sets(self) -> None:
        game = _game()
        handler = CallResponseGameHandler()
        handler.setup(game)

        assert handler.get_available_moves(game) == ["taunt", "both"]
        assert game.opponent_next_move is None
        handler.receive_move(game, "taunt")

        assert handler.get_available_moves(game) == ["rebuttal", "both"]
        assert game.opponent_next_move == "taunt"

    def test_explicit_negative_result_retains_its_authored_source(self) -> None:
        game = _game()
        game.player_phrase_ids = ["both"]
        game.opponent_phrase_ids = ["miss"]
        handler = CallResponseGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, "both")

        assert result is RoundResult.WIN
        assert game.history[-1].notes["matched"] is False
        assert game.history[-1].notes["match_source_id"] == "explicit-negative"

    def test_missing_role_capability_fails_without_a_kernel_fallback(self) -> None:
        game = _game()
        game.player_phrase_ids = ["rebuttal"]
        handler = CallResponseGameHandler()
        handler.setup(game)

        with pytest.raises(ValueError, match="No call-capable phrases"):
            handler.get_available_moves(game)

    def test_move_labels_and_journal_make_the_exchange_legible(self) -> None:
        game = _game()
        handler = CallResponseGameHandler()
        handler.setup(game)

        assert handler.get_move_label(game, "taunt") == "Call with You fight like a dairy farmer."
        handler.receive_move(game, "taunt")
        fragments = handler.get_journal_fragments(game)

        call, response, outcome = fragments
        assert (call.who, call.how, call.content) == (
            "You",
            "calls",
            "You fight like a dairy farmer.",
        )
        assert (response.who, response.how, response.content) == (
            "Opponent",
            "answers",
            "How appropriate.",
        )
        assert outcome.fragment_type == "content"
        assert outcome.content == (
            "Opponent wins the exchange. Score: you 0, opponent 1. Initiative: the opponent."
        )

    def test_namespace_uses_a_qualified_initiative_key(self) -> None:
        game = _game(player_has_initiative=False)
        handler = CallResponseGameHandler()
        handler.setup(game)

        namespace = game.to_namespace()

        assert namespace["call_response_player_has_initiative"] is False
        assert "player_has_initiative" not in namespace


class TestCallResponsePersistence:
    """Configured state and exchange history survive graph persistence."""

    def test_graph_round_trip_retains_schedule_initiative_and_notes(self) -> None:
        graph = Graph(label="call-response-persistence")
        block = graph.add_node(kind=CallResponseBlock, label="contest")
        block.game_state = _game()
        handler = block.game_handler
        handler.setup(block.game)
        handler.receive_move(block.game, "taunt")

        json.dumps(block.game.model_dump(mode="json"))
        restored_graph = Graph.structure(graph.unstructure())
        restored = restored_graph.find_one(Selector(label="contest"))

        assert isinstance(restored, CallResponseBlock)
        assert restored.game.phrases["taunt"].roles == ["call"]
        assert restored.game.schedule[0].source_id == "dairy-rebuttal"
        assert restored.game.player_has_initiative is False
        assert isinstance(restored.game.last_exchange, CallResponseExchange)
        assert restored.game.last_exchange == block.game.last_exchange
        assert restored.game.history[-1].notes == block.game.history[-1].notes


class TestCallResponseVmIntegration:
    """The kernel enters and re-enters through the generic game lifecycle."""

    def test_accepted_entry_projects_moves_and_journals_the_selected_exchange(self) -> None:
        graph = Graph(label="call-response-vm")
        foyer = graph.add_node(kind=Block, label="foyer")
        contest = graph.add_node(kind=CallResponseBlock, label="contest")
        contest.game_state = _game()
        entry = TraversableEdge(
            graph=graph,
            predecessor_id=foyer.uid,
            successor_id=contest.uid,
            label="Begin exchange",
        )
        ledger = Ledger.from_graph(graph=graph, entry_id=foyer.uid)

        ledger.resolve_choice(entry.uid)

        assert contest.game.phase is GamePhase.READY
        action = next(
            edge
            for edge in contest.edges_out()
            if isinstance(edge, Action) and edge.payload == {"move": "taunt"}
        )
        assert action.label == "Call with You fight like a dairy farmer."

        ledger.resolve_choice(action.uid, choice_payload=action.payload)

        assert contest.game.history[-1].notes["matched"] is True
        assert any(
            fragment.who == "Opponent"
            and fragment.how == "answers"
            and fragment.content == "How appropriate."
            for fragment in ledger.get_journal()
            if isinstance(fragment, AttributedFragment)
        )
