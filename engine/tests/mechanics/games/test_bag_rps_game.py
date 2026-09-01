"""Tests for the aggregate-force Bag-RPS contest."""

from __future__ import annotations

import pytest

from tangl.core import Graph
from tangl.mechanics.games import GameTokenSpec, HasGame
from tangl.mechanics.games.aggregate_force_game import ForceCommitMove, ForceDisposition
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


class TestCommitmentCycle:
    """Commitment is a transfer, and every committed token gets routed."""

    def _game(self, **kwargs) -> BagRpsGame:
        config = {
            "player_opening_reserve": {"rock": 3, "paper": 1},
            "opponent_opening_reserve": {"scissors": 3},
        }
        config.update(kwargs)
        return BagRpsGame(**config)

    def _clash(self, game: BagRpsGame) -> BagRpsGameHandler:
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.resolve_round(
            game,
            ForceCommitMove(profile=(("rock", 2),)),
            ForceCommitMove(profile=(("scissors", 2),)),
        )
        return handler

    def test_committing_moves_tokens_out_of_the_reserve(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)

        moved = handler.commit_forces(game, "player", {"rock": 2})

        assert moved == {"rock": 2}
        assert game.player_reserve.amounts == {"rock": 1, "paper": 1}
        assert game.player_active.amounts == {"rock": 2}

    def test_a_commitment_cannot_overdraw_the_reserve(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)

        moved = handler.commit_forces(game, "player", {"paper": 5})

        assert moved == {"paper": 1}
        assert game.player_active.amounts == {"paper": 1}

    def test_survivors_retire_to_the_reserve_by_default(self) -> None:
        game = self._game()
        self._clash(game)

        # Rock beats scissors, but the disadvantaged trade ratio still buys the
        # losing side one casualty, so one of the committed pair comes home.
        assert game.player_active.amounts == {}
        assert game.player_eliminated["rock"] == 1
        assert game.player_reserve["rock"] == 2

    def test_conserved_survivors_stay_in_play(self) -> None:
        game = self._game(survivor_disposition=ForceDisposition.CONSERVE)
        self._clash(game)

        assert game.player_active["rock"] == 1
        assert game.player_reserve["rock"] == 1

    def test_ceded_survivors_cross_to_the_opponent(self) -> None:
        game = self._game(survivor_disposition=ForceDisposition.CEDE)
        self._clash(game)

        assert game.player_active.amounts == {}
        assert game.opponent_reserve["rock"] == 1

    def test_casualties_leave_the_game_entirely(self) -> None:
        game = self._game()
        self._clash(game)

        assert game.opponent_eliminated["scissors"] == 2
        assert game.opponent_reserve["scissors"] == 1

    def test_a_side_is_not_beaten_while_its_force_is_committed(self) -> None:
        game = self._game(survivor_disposition=ForceDisposition.CONSERVE)
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.commit_forces(game, "player", {"rock": 3, "paper": 1})

        assert game.player_reserve.amounts == {}
        assert game.standing_force("player") == 4
        assert handler.evaluate(game).name == "IN_PROCESS"


class TestReserveAdjustmentAndRetraining:
    """Seams for pressure that does not come out of a fight."""

    def _game(self) -> BagRpsGame:
        return BagRpsGame(
            force_types=["blue_0", "blue_1", "sharp"],
            force_beats={"rock": "scissors", "paper": "rock", "scissors": "paper"},
            token_specs={
                "blue_0": GameTokenSpec(affiliation="rock", value=1),
                "blue_1": GameTokenSpec(affiliation="rock", value=2),
                "sharp": GameTokenSpec(affiliation="scissors", value=1),
            },
            player_opening_reserve={"blue_0": 3},
            opponent_opening_reserve={"sharp": 2},
        )

    def test_fresh_recruits_augment_the_reserve(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)

        record = handler.adjust_reserve(
            game, "player", {"blue_0": 2}, reason="a surge of fresh recruits"
        )

        assert game.player_reserve["blue_0"] == 5
        assert record["gained"] == {"blue_0": 2}
        assert record["reason"] == "a surge of fresh recruits"

    def test_a_plague_at_home_hobbles_the_reserve(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)

        record = handler.adjust_reserve(game, "player", {"blue_0": -2}, reason="plague")

        assert game.player_reserve["blue_0"] == 1
        assert game.player_eliminated["blue_0"] == 2
        assert record["lost"] == {"blue_0": 2}

    def test_a_reserve_cannot_be_hobbled_below_empty(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)

        handler.adjust_reserve(game, "player", {"blue_0": -99})

        assert game.player_reserve["blue_0"] == 0
        assert game.player_eliminated["blue_0"] == 3

    def test_promotion_walks_the_weight_ladder_within_a_colour(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)

        assert game.rank_ladder("rock") == ["blue_0", "blue_1"]

        record = handler.retrain(game, "player", "blue_0", 2, reason="brevet")

        assert record["to"] == "blue_1"
        assert record["direction"] == "promote"
        assert game.player_reserve.amounts == {"blue_0": 1, "blue_1": 2}

    def test_demotion_walks_the_other_way(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.retrain(game, "player", "blue_0", 3)

        record = handler.retrain(game, "player", "blue_1", 1, steps=-1, reason="injury")

        assert record["to"] == "blue_0"
        assert record["direction"] == "demote"
        assert game.player_reserve.amounts == {"blue_1": 2, "blue_0": 1}

    def test_promotion_off_the_end_of_the_ladder_is_a_no_op(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.retrain(game, "player", "blue_0", 3)

        assert handler.retrain(game, "player", "blue_1", 1) is None
        assert game.player_reserve.amounts == {"blue_1": 3}

    def test_retraining_can_target_committed_tokens(self) -> None:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.commit_forces(game, "player", {"blue_0": 2})

        handler.retrain(game, "player", "blue_0", 1, pool="active", reason="field brevet")

        assert game.player_active.amounts == {"blue_0": 1, "blue_1": 1}
        assert game.player_reserve.amounts == {"blue_0": 1}


class TestTransmutation:
    """Owner, affiliation, and weight are three independent axes."""

    def _game(self) -> BagRpsGame:
        return BagRpsGame(
            force_types=["blue_0", "blue_1", "red_0"],
            force_beats={"rock": "scissors", "paper": "rock", "scissors": "paper"},
            token_specs={
                "blue_0": GameTokenSpec(affiliation="rock", value=1),
                "blue_1": GameTokenSpec(affiliation="rock", value=2),
                "red_0": GameTokenSpec(affiliation="paper", value=1),
            },
            player_opening_reserve={"blue_0": 3},
            opponent_opening_reserve={"red_0": 2},
        )

    def _ready(self) -> tuple[BagRpsGame, BagRpsGameHandler]:
        game = self._game()
        handler = BagRpsGameHandler()
        handler.setup(game)
        return game, handler

    def test_a_token_can_change_sides(self) -> None:
        game, handler = self._ready()

        record = handler.transmute(
            game, "player", "blue_0", "blue_0", 1,
            to_owner="opponent", reason="bought off",
        )

        assert record["changes"] == ["defect"]
        assert game.player_reserve["blue_0"] == 2
        assert game.opponent_reserve["blue_0"] == 1

    def test_a_token_can_change_affiliation(self) -> None:
        game, handler = self._ready()

        record = handler.transmute(game, "player", "blue_0", "red_0", 1)

        assert record["changes"] == ["metamorphosis"]
        assert game.player_reserve.amounts == {"blue_0": 2, "red_0": 1}

    def test_a_token_can_change_weight(self) -> None:
        game, handler = self._ready()

        record = handler.transmute(game, "player", "blue_0", "blue_1", 1)

        assert record["changes"] == ["ameliorate"]

    def test_decay_is_the_other_direction(self) -> None:
        game, handler = self._ready()
        handler.transmute(game, "player", "blue_0", "blue_1", 2)

        record = handler.transmute(game, "player", "blue_1", "blue_0", 1)

        assert record["changes"] == ["decay"]

    def test_several_axes_can_change_at_once(self) -> None:
        game, handler = self._ready()

        record = handler.transmute(
            game, "player", "blue_1", "red_0", 1,
            to_owner="opponent", reason="a defector, transformed and diminished",
        )

        # nothing to move: the player holds no blue_1 yet
        assert record is None

        handler.transmute(game, "player", "blue_0", "blue_1", 1)
        record = handler.transmute(
            game, "player", "blue_1", "red_0", 1, to_owner="opponent",
        )

        assert record["changes"] == ["defect", "metamorphosis", "decay"]
        assert game.opponent_reserve["red_0"] == 3

    def test_transmutation_can_cross_pools(self) -> None:
        game, handler = self._ready()
        handler.commit_forces(game, "player", {"blue_0": 2})

        record = handler.transmute(
            game, "player", "blue_0", "blue_1", 1, pool="active", to_pool="reserve",
        )

        assert record["pool"] == "active"
        assert record["to_pool"] == "reserve"
        assert game.player_active.amounts == {"blue_0": 1}
        assert game.player_reserve.amounts == {"blue_0": 1, "blue_1": 1}


class TestAttritionPolicies:
    """How much force dies, and whose, is a named and swappable choice."""

    def _run(self, policy: str, player: int, opponent: int, **kwargs) -> tuple[dict, dict]:
        game = BagRpsGame(
            casualty_policy=policy,
            max_commit_size=20,
            player_opening_reserve={"rock": player},
            opponent_opening_reserve={"scissors": opponent},
            **kwargs,
        )
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.resolve_round(
            game,
            ForceCommitMove(profile=(("rock", player),)),
            ForceCommitMove(profile=(("scissors", opponent),)),
        )
        detail = game.round_detail or {}
        return detail["player_losses"], detail["opponent_losses"]

    def test_trade_ratio_remains_the_default(self) -> None:
        assert BagRpsGame().casualty_policy == "trade_ratio"

    def test_proportional_power_costs_the_loser_more(self) -> None:
        player_losses, opponent_losses = self._run("proportional_power", 5, 5)

        # rock beats scissors, so the winning side bleeds less
        assert sum(player_losses.values()) < sum(opponent_losses.values())

    def test_a_small_commitment_is_not_annihilated_by_a_large_one(self) -> None:
        # Denominating each quota against the *combined* pool would wipe the
        # smaller bag out entirely, because the rate would be calibrated on
        # force that was never its own.
        _, opponent_losses = self._run("proportional_power", 7, 3)

        assert sum(opponent_losses.values()) < 3

    def test_losses_scale_with_the_size_of_your_own_commitment(self) -> None:
        _, small = self._run("proportional_power", 7, 3)
        _, large = self._run("proportional_power", 7, 9)

        assert sum(large.values()) > sum(small.values())

    def test_a_gentler_rate_kills_less(self) -> None:
        _, heavy = self._run("proportional_power", 6, 6, decimation_rate=0.5)
        _, light = self._run("proportional_power", 6, 6, decimation_rate=0.1)

        assert sum(heavy.values()) > sum(light.values())

    def test_heavy_tokens_absorb_more_of_a_power_quota(self) -> None:
        # Two weight-2 tokens satisfy a quota that would cost four light ones.
        game = BagRpsGame(
            casualty_policy="proportional_power",
            force_types=["heavy", "sharp"],
            force_beats={"rock": "scissors", "paper": "rock", "scissors": "paper"},
            token_specs={
                "heavy": GameTokenSpec(affiliation="rock", value=4),
                "sharp": GameTokenSpec(affiliation="scissors", value=1),
            },
            max_commit_size=20,
            player_opening_reserve={"heavy": 2},
            opponent_opening_reserve={"sharp": 8},
        )
        handler = BagRpsGameHandler()
        handler.setup(game)
        handler.resolve_round(
            game,
            ForceCommitMove(profile=(("heavy", 2),)),
            ForceCommitMove(profile=(("sharp", 8),)),
        )
        detail = game.round_detail or {}

        # equal power on both sides, but one heavy token pays a whole quota
        assert sum(detail["player_losses"].values()) <= 1

    def test_an_unknown_policy_is_an_error_not_a_silent_default(self) -> None:
        game = BagRpsGame(casualty_policy="no_such_policy")
        handler = BagRpsGameHandler()
        handler.setup(game)

        with pytest.raises(KeyError):
            handler.resolve_attrition(game)
