"""Tests for the aggregate-force Bag-RPS contest."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.bag_rps_game import BagRpsGame, BagRpsGameHandler
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


def _profile(**counts: int) -> dict[str, int]:
    return {label: count for label, count in counts.items() if count > 0}


class BagRpsBlock(HasGame, Block):
    """Test block embedding a Bag-RPS game."""

    _game_class = BagRpsGame
    _game_handler_class = BagRpsGameHandler


class TestBagRpsCore:
    """Core aggregate-force behavior tests."""

    def test_two_rock_can_tie_one_paper(self) -> None:
        game = BagRpsGame(
            player_opening_reserve={"rock": 2},
            opponent_opening_reserve={"paper": 1},
        )
        handler = BagRpsGameHandler()
        handler.setup(game)
        move = next(move for move in handler.get_available_moves(game) if move.as_dict() == _profile(rock=2))

        result = handler.receive_move(game, move)

        assert result.name == "DRAW"
        assert game.score == {"player": 1, "opponent": 1}
        assert game.opponent_reserve["paper"] == 0

    def test_paper_and_scissors_can_tie_one_rock(self) -> None:
        game = BagRpsGame(
            player_opening_reserve={"paper": 1, "scissors": 1},
            opponent_opening_reserve={"rock": 1},
            max_commit_size=2,
            max_mix_types=2,
        )
        handler = BagRpsGameHandler()
        handler.setup(game)
        move = next(
            move for move in handler.get_available_moves(game) if move.as_dict() == _profile(paper=1, scissors=1)
        )

        result = handler.receive_move(game, move)

        assert result.name == "DRAW"
        assert game.score == {"player": 1, "opponent": 1}

    def test_paper_and_scissors_can_lose_to_two_rock(self) -> None:
        game = BagRpsGame(
            player_opening_reserve={"paper": 1, "scissors": 1},
            opponent_opening_reserve={"rock": 2},
            max_commit_size=2,
            max_mix_types=2,
        )
        handler = BagRpsGameHandler()
        handler.setup(game)
        move = next(
            move for move in handler.get_available_moves(game) if move.as_dict() == _profile(paper=1, scissors=1)
        )

        result = handler.receive_move(game, move)

        assert result.name == "LOSE"
        assert game.score == {"player": 1, "opponent": 2}
        assert game.player_reserve == {"paper": 0, "scissors": 0}

    def test_move_generation_respects_commit_bounds(self) -> None:
        game = BagRpsGame(
            player_opening_reserve={"rock": 3, "paper": 2, "scissors": 1},
            opponent_opening_reserve={"rock": 1},
            max_commit_size=2,
            max_mix_types=1,
        )
        handler = BagRpsGameHandler()
        handler.setup(game)

        profiles = [move.as_dict() for move in handler.get_available_moves(game)]

        assert _profile(rock=3) not in profiles
        assert _profile(rock=1, paper=1) not in profiles
        assert _profile(rock=2) in profiles


class TestBagRpsIntegration:
    """VM and HasGame integration tests for Bag-RPS."""

    def test_move_labels_describe_commitment_profiles(self) -> None:
        graph = Graph(label="bag_rps_labels")
        block = graph.add_node(kind=BagRpsBlock, label="pit")
        block.game.player_opening_reserve = {"rock": 2, "paper": 1}
        block.game.opponent_opening_reserve = {"paper": 1}
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)

        assert "Commit 2 rock" in [action.label for action in actions]
        assert "Commit 1 rock + 1 paper" in [action.label for action in actions]

    def test_bag_rps_routes_to_victory_when_opponent_reserve_collapses(self) -> None:
        graph = Graph(label="bag_rps_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = BagRpsBlock.create_game_block(
            graph=graph,
            game_class=BagRpsGame,
            handler_class=BagRpsGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="pit",
        )
        block.game.player_opening_reserve = {"rock": 2}
        block.game.opponent_opening_reserve = {"paper": 1}
        block.game.max_commit_size = 2
        block.game.opponent_strategy = "aggregate_force_greedy"
        block.game_handler.setup(block.game)

        intro_to_pit = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Commit a force",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_pit.uid)

        commit = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Commit 2 rock"
        )
        ledger.resolve_choice(commit.uid, choice_payload=commit.payload)

        assert ledger.cursor_id == victory.uid
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "reserve now stands" in content.lower()

    def test_context_exports_reserve_pressure(self) -> None:
        graph = Graph(label="bag_rps_context")
        block = graph.add_node(kind=BagRpsBlock, label="pit")
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["aggregate_player_force"] > 0
        assert namespace["bag_rps_player_reserve"]
