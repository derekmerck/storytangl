"""Tests for the asymmetric Siege-RPS aggregate-force variant."""

from __future__ import annotations

from tangl.core import Graph
from tangl.story.concepts.asset import AssetWallet
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.mechanics.games.aggregate_force_game import ForceDisposition
from tangl.mechanics.games.siege_rps_game import ForceCommitMove, SiegeRpsGame, SiegeRpsGameHandler
from tangl.story import Action, Block
from tangl.vm import Frame


def _profile(**counts: int) -> dict[str, int]:
    return {label: count for label, count in counts.items() if count > 0}


class SiegeBlock(HasGame, Block):
    """Test block embedding Siege-RPS."""

    _game_class = SiegeRpsGame
    _game_handler_class = SiegeRpsGameHandler


class TestSiegeRpsCore:
    """Core initiative and attrition tests."""

    def test_defender_can_beat_attack_and_flip_initiative(self) -> None:
        game = SiegeRpsGame(
            player_opening_reserve={"rock": 3},
            opponent_opening_reserve={"paper": 1},
            initial_player_has_initiative=False,
        )
        handler = SiegeRpsGameHandler()
        handler.setup(game)

        defend = next(move for move in handler.get_available_moves(game) if move.as_dict() == _profile(rock=3))
        result = handler.receive_move(game, defend)

        assert result.name == "WIN"
        assert game.player_has_initiative is True

    def test_meeting_attack_preserves_attacker_initiative(self) -> None:
        game = SiegeRpsGame(
            player_opening_reserve={"rock": 2},
            opponent_opening_reserve={"paper": 1},
            initial_player_has_initiative=False,
        )
        handler = SiegeRpsGameHandler()
        handler.setup(game)

        defend = next(move for move in handler.get_available_moves(game) if move.as_dict() == _profile(rock=2))
        result = handler.receive_move(game, defend)

        assert result.name == "DRAW"
        assert game.player_has_initiative is False

    def test_reserve_exhaustion_can_end_after_initiative_flip(self) -> None:
        game = SiegeRpsGame(
            player_opening_reserve={"rock": 5},
            opponent_opening_reserve={"paper": 4},
            initial_player_has_initiative=False,
            max_commit_size=4,
            disadvantaged_trade_ratio=1,
        )
        handler = SiegeRpsGameHandler()
        handler.setup(game)
        game.opponent_next_move = ForceCommitMove(profile=(("paper", 3),))

        defend = next(move for move in handler.get_available_moves(game) if move.as_dict() == _profile(rock=4))
        handler.receive_move(game, defend)
        attack = next(move for move in handler.get_available_moves(game) if move.as_dict() == _profile(rock=2))
        result = handler.receive_move(game, attack)

        assert result.name in {"DRAW", "WIN"}
        assert game.result.name == "WIN"
        assert game.opponent_reserve["paper"] == 0


class TestSiegeRpsIntegration:
    """Integration tests for the asymmetric variant."""

    def test_move_labels_reflect_attack_or_answer_role(self) -> None:
        graph = Graph(label="siege_labels")
        block = graph.add_node(kind=SiegeBlock, label="siege")
        block.game.player_opening_reserve = {"rock": 5}
        block.game.opponent_opening_reserve = {"paper": 4}
        block.game.initial_player_has_initiative = False
        block.game.max_commit_size = 4
        block.game.disadvantaged_trade_ratio = 1
        block.game_handler.setup(block.game)
        block.game.opponent_next_move = ForceCommitMove(profile=(("paper", 3),))

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        labels = [action.label for action in provision_game_moves(block, ctx=ctx)]
        assert any(label.startswith("Answer with") for label in labels)

        defend = next(move for move in block.game_handler.get_available_moves(block.game) if move.as_dict() == _profile(rock=4))
        block.game_handler.receive_move(block.game, defend)
        block.game.player_has_initiative = True
        labels = [action.label for action in provision_game_moves(block, ctx=ctx)]
        assert any(label.startswith("Attack with") for label in labels)

    def test_context_exports_initiative_and_signal(self) -> None:
        graph = Graph(label="siege_context")
        block = graph.add_node(kind=SiegeBlock, label="siege")
        block.game.initial_player_has_initiative = False
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["siege_player_has_initiative"] is False
        assert namespace["siege_opponent_signal"] is not None


class TestConservedForceRemainsOnTheField:
    """Casualties fall on everything standing, not only this round's commit."""

    def _game(self, **kwargs) -> SiegeRpsGame:
        config = {
            "survivor_disposition": ForceDisposition.CONSERVE,
            "player_opening_reserve": {"rock": 6},
            "opponent_opening_reserve": {"scissors": 6},
            "max_commit_size": 1,
        }
        config.update(kwargs)
        return SiegeRpsGame(**config)

    def _commit(self, handler, game, player_label, opponent_label) -> None:
        game.opponent_next_move = ForceCommitMove(profile=((opponent_label, 1),))
        handler.receive_move(game, ForceCommitMove(profile=((player_label, 1),)))

    def test_survivors_accumulate_across_rounds(self) -> None:
        game = self._game()
        handler = SiegeRpsGameHandler()
        handler.setup(game)

        self._commit(handler, game, "rock", "scissors")
        assert game.player_active.amounts == {"rock": 1}

        self._commit(handler, game, "rock", "scissors")
        assert game.player_active.amounts == {"rock": 2}

    def test_allocation_sees_standing_force_not_just_the_commit(self) -> None:
        # The defect: casualties were allocated against the dict returned by
        # commit_forces, so conserved survivors were invisible as targets. The
        # budget is capped by the defender's size, so a two-rock standing force
        # can lose more than a one-rock commitment.
        game = self._game()
        handler = SiegeRpsGameHandler()
        handler.setup(game)
        game.player_active.gain({"rock": 2})
        game.opponent_active.gain({"paper": 3})

        commit_only = AssetWallet(amounts={"rock": 1})
        from_commit = handler._allocate_casualties(
            game, game.opponent_active, commit_only
        )
        from_standing = handler._allocate_casualties(
            game, game.opponent_active, game.player_active
        )

        assert sum(from_commit.values()) == 1
        assert sum(from_standing.values()) == 2

    def test_holdings_are_wallets_throughout_allocation(self) -> None:
        game = self._game()
        handler = SiegeRpsGameHandler()
        handler.setup(game)
        self._commit(handler, game, "rock", "scissors")

        losses = handler._allocate_casualties(
            game, game.opponent_active, game.player_active
        )

        assert isinstance(losses, dict)
        assert all(isinstance(count, int) for count in losses.values())
