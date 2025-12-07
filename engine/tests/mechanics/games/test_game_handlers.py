from __future__ import annotations

"""Unit tests for VM handlers integrating :class:`HasGame`."""

import pytest

from tangl.core import Graph
from tangl.mechanics.games import Game, GameHandler, GamePhase, GameResult, RoundResult, HasGame
from tangl.story.episode import Action, Block
from tangl.mechanics.games.handlers import (
    generate_game_journal,
    inject_game_context,
    process_game_move,
    provision_game_moves,
    setup_game_on_first_visit,
)
from tangl.vm import Frame


class SampleGame(Game):
    """Minimal game for exercising handlers."""

    __test__ = False

    def get_available_moves(self) -> list[str]:  # type: ignore[override]
        return ["win", "lose", "draw"]


class TestGameHandler(GameHandler[SampleGame]):
    """Simple handler that maps moves directly to outcomes."""

    def get_available_moves(self, game: SampleGame) -> list[str]:
        return ["win", "lose", "draw"]

    def resolve_round(
        self, game: SampleGame, player_move: str, opponent_move: str | None
    ) -> RoundResult:
        if player_move == "win":
            game.score["player"] += 1
            return RoundResult.WIN
        if player_move == "lose":
            game.score["opponent"] += 1
            return RoundResult.LOSE
        return RoundResult.DRAW

    def evaluate(self, game: SampleGame) -> GameResult:
        if game.last_round is None:
            return GameResult.IN_PROCESS
        return game.last_round.result.to_game_result()


class GameBlock(HasGame, Block):
    """Test block combining HasGame with Block."""

    _game_class = SampleGame
    _game_handler_class = TestGameHandler


@pytest.fixture()
def game_graph() -> Graph:
    return Graph(label="game_graph")


@pytest.fixture()
def game_block(game_graph: Graph) -> GameBlock:
    return game_graph.add_node(obj_cls=GameBlock, label="game_block")


def make_frame(graph: Graph, cursor_id):
    frame = Frame(graph=graph, cursor_id=cursor_id, cursor_history=[cursor_id])
    # build context to attach _frame on the instance
    _ = frame.context
    return frame


class TestSetupHandler:
    def test_setup_on_first_visit_initializes_game(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        assert game_block.game.phase is GamePhase.PENDING

        setup_game_on_first_visit(game_block, ctx=ctx)

        assert game_block.game.phase is GamePhase.READY
        assert game_block.locals["game_initialized"] is True

    def test_setup_skips_on_revisit(self, game_graph: Graph, game_block: GameBlock):
        frame = Frame(
            graph=game_graph, cursor_id=game_block.uid, cursor_history=[game_block.uid, game_block.uid]
        )
        ctx = frame.context

        setup_game_on_first_visit(game_block, ctx=ctx)

        assert "game_initialized" not in game_block.locals
        assert game_block.game.phase is GamePhase.PENDING

    def test_setup_idempotent_when_ready(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        game_block.game_handler.setup(game_block.game)
        game_block.locals.clear()

        setup_game_on_first_visit(game_block, ctx=ctx)

        assert "game_initialized" not in game_block.locals
        assert game_block.game.phase is GamePhase.READY


class TestProvisioningHandler:
    def test_moves_provisioned_when_ready(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        game_block.game.phase = GamePhase.READY

        actions = provision_game_moves(game_block, ctx=ctx)

        assert len(actions) == 3
        assert all(isinstance(action, Action) for action in actions)
        assert all(action.source_id == game_block.uid for action in actions)
        assert all(action.destination_id == game_block.uid for action in actions)
        assert all(action.payload == {"move": move} for action, move in zip(actions, ["win", "lose", "draw"]))

    def test_no_moves_when_not_ready(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        game_block.game.phase = GamePhase.PENDING

        actions = provision_game_moves(game_block, ctx=ctx)

        assert actions == []


class TestUpdateHandler:
    def test_move_processing_stores_results(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        game_block.game_handler.setup(game_block.game)

        action = Action(
            graph=game_graph,
            source_id=game_block.uid,
            destination_id=game_block.uid,
            payload={"move": "win"},
        )

        frame.resolve_choice(action)

        assert game_block.game.round == 1
        assert game_block.locals["round_result"] is RoundResult.WIN
        assert game_block.locals["game_result"] is GameResult.WIN
        assert game_block.locals["last_round"].player_move == "win"

    def test_move_ignored_without_payload(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        game_block.game_handler.setup(game_block.game)
        frame.selected_edge = Action(
            graph=game_graph,
            source_id=game_block.uid,
            destination_id=game_block.uid,
            payload=None,
        )

        process_game_move(game_block, ctx=ctx)

        assert "round_result" not in game_block.locals
        assert game_block.game.round == 0


class TestJournalHandler:
    def test_journal_generation_from_last_round(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        game_block.game_handler.setup(game_block.game)
        action = Action(
            graph=game_graph,
            source_id=game_block.uid,
            destination_id=game_block.uid,
            payload={"move": "lose"},
        )
        frame.selected_edge = action
        process_game_move(game_block, ctx=ctx)

        fragments = generate_game_journal(game_block, ctx=ctx)

        assert fragments
        assert any("You played" in fragment.content for fragment in fragments)
        assert any("lost this round" in fragment.content for fragment in fragments)
        assert any("Score" in fragment.content for fragment in fragments)

    def test_no_fragments_without_round(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        fragments = generate_game_journal(game_block, ctx=ctx)

        assert fragments == []


class TestContextHandler:
    def test_context_exports_predicates(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = frame.context

        game_block.game.result = GameResult.DRAW
        game_block.game.round = 2

        namespace = inject_game_context(game_block, ctx=ctx)

        assert namespace["game_draw"] is True
        assert namespace["game_won"] is False
        assert namespace["game_round"] == 2
