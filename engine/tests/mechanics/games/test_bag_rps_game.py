"""Tests for the aggregate-force Bag-RPS contest."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import GameTokenSpec, HasGame
from tangl.mechanics.games.aggregate_force_game import ForceCommitMove
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
        # The reserve is a wallet, so exhausted token types drop out entirely
        # rather than lingering as zero counts.
        assert game.player_reserve.amounts == {}

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
        content = " ".join(
            fragment.content
            for fragment in ledger.get_journal()
            if isinstance(fragment.content, str)
        )
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


class TestWeightedAndColouredTokens:
    """Many sizes of a type, many types, or both in one bag."""

    def _game(self, **kwargs) -> BagRpsGame:
        config = {
            "force_types": ["brute", "heavy_brute", "fast", "sharp"],
            "force_beats": {"rock": "scissors", "paper": "rock", "scissors": "paper"},
            "token_specs": {
                "brute": GameTokenSpec(affiliation="rock", value=1),
                "heavy_brute": GameTokenSpec(affiliation="rock", value=3),
                "fast": GameTokenSpec(affiliation="paper", value=1),
                "sharp": GameTokenSpec(affiliation="scissors", value=1),
            },
            "player_opening_reserve": {"brute": 2, "heavy_brute": 1, "fast": 1},
            "opponent_opening_reserve": {"sharp": 3},
        }
        config.update(kwargs)
        return BagRpsGame(**config)

    def test_several_labels_can_share_one_affiliation(self) -> None:
        game = self._game()

        assert game.get_force_affiliation("brute") == "rock"
        assert game.get_force_affiliation("heavy_brute") == "rock"
        assert game.get_force_weight("heavy_brute") == 3

    def test_dominant_affiliation_weighs_size_against_count(self) -> None:
        game = self._game()
        BagRpsGameHandler().setup(game)

        # one heavy brute plus two light outweighs a single fast marker
        assert game.dominant_affiliation(game.player_reserve) == "rock"

    def test_a_heavy_token_hits_harder_than_a_light_one(self) -> None:
        # The defender must be deep enough that the casualty budget is not
        # capped by its own size, or weight cannot show through.
        handler = BagRpsGameHandler()
        results = []
        for label in ("brute", "heavy_brute"):
            game = self._game(
                player_opening_reserve={label: 1},
                opponent_opening_reserve={"sharp": 3},
            )
            handler.setup(game)
            handler.resolve_round(
                game,
                ForceCommitMove(profile=((label, 1),)),
                ForceCommitMove(profile=(("sharp", 3),)),
            )
            results.append(game.score["player"])

        assert results == [1, 3]

    def test_dominance_is_evaluated_between_affiliations(self) -> None:
        # heavy_brute is "rock" and must beat "scissors" despite the label
        # sharing no name with either side of the declared cycle
        game = self._game(
            player_opening_reserve={"heavy_brute": 1},
            opponent_opening_reserve={"sharp": 1},
        )
        handler = BagRpsGameHandler()
        handler.setup(game)

        result = handler.resolve_round(
            game,
            ForceCommitMove(profile=(("heavy_brute", 1),)),
            ForceCommitMove(profile=(("sharp", 1),)),
        )

        assert result.name == "WIN"
        assert game.opponent_reserve.amounts == {}

    def test_undeclared_contests_keep_label_as_affiliation(self) -> None:
        # The stock rock/paper/scissors bag declares no specs at all.
        plain = BagRpsGame()

        assert plain.get_force_affiliation("rock") == "rock"
        assert plain.get_force_weight("rock") == 1
