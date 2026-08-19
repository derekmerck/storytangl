from __future__ import annotations

"""Unit tests for VM handlers integrating :class:`HasGame`."""

import pytest

from tangl.core import Graph
from tangl.journal.fragments import ContentFragment
from tangl.journal.intent import PieceConstraints, PiecesAccepts
from tangl.mechanics.games import Game, GameHandler, GamePhase, GameResult, RoundResult, HasGame
from tangl.story import Action, Block
from tangl.mechanics.games.handlers import (
    generate_game_journal,
    inject_game_context,
    process_game_move,
    provision_game_moves,
)
from tangl.vm import Frame, ResolutionPhase, TraversableEdge, VmPhaseCtx


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


class ContextJournalHandler(TestGameHandler):
    """Confirms the generic JOURNAL chokepoint forwards its live context."""

    received_ctx: VmPhaseCtx | None = None

    def get_journal_fragments(
        self,
        game: SampleGame,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[ContentFragment]:
        self.received_ctx = ctx
        return [ContentFragment(content="Context-aware journal.")]


class GameBlock(HasGame, Block):
    """Test block combining HasGame with Block."""

    _game_class = SampleGame
    _game_handler_class = TestGameHandler


class StableGameHandler(TestGameHandler):
    """Handler whose authored move edges are stable rather than projected."""

    dynamic_move_projection = False


class PresentationGameHandler(TestGameHandler):
    """Records planning preflight without treating it as game setup."""

    presentation_calls: int = 0

    def provision_presentation(self, game: SampleGame, *, ctx: VmPhaseCtx) -> None:
        self.presentation_calls += 1


class PresentationGameBlock(HasGame, Block):
    """Test block whose handler has a pending-game presentation preflight."""

    _game_class = SampleGame
    _game_handler_class = PresentationGameHandler


class StableGameBlock(HasGame, Block):
    """Test block for stable game-action lifetime."""

    _game_class = SampleGame
    _game_handler_class = StableGameHandler


@pytest.fixture()
def game_graph() -> Graph:
    return Graph(label="game_graph")


def _add_node(graph: Graph, *, kind, **attrs):
    return graph.add_node(kind=kind, **attrs)


@pytest.fixture()
def game_block(game_graph: Graph) -> GameBlock:
    return _add_node(game_graph, kind=GameBlock, label="game_block")


def make_frame(graph: Graph, cursor_id):
    cursor = graph.get(cursor_id)
    return Frame(graph=graph, cursor=cursor)


def make_ctx(frame: Frame):
    return frame._make_ctx(
        incoming_edge=frame.selected_edge,
        incoming_payload=frame.selected_payload,
    )


class TestProvisioningHandler:
    def test_moves_provisioned_when_ready(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        game_block.game.phase = GamePhase.READY

        actions = provision_game_moves(game_block, ctx=ctx)

        assert len(actions) == 3
        assert all(isinstance(action, Action) for action in actions)
        assert all(action.predecessor_id == game_block.uid for action in actions)
        assert all(action.successor_id == game_block.uid for action in actions)
        assert all(
            action.payload == {"move": move}
            for action, move in zip(actions, ["win", "lose", "draw"], strict=True)
        )

    def test_provisioning_replaces_previous_dynamic_game_actions(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        game_block.game.phase = GamePhase.READY

        first = provision_game_moves(game_block, ctx=ctx)
        second = provision_game_moves(game_block, ctx=ctx)
        actions = [edge for edge in game_block.edges_out() if isinstance(edge, Action)]

        assert len(first) == 3
        assert len(second) == 3
        assert len(actions) == 3

    def test_no_moves_when_not_ready(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        game_block.game.phase = GamePhase.PENDING

        actions = provision_game_moves(game_block, ctx=ctx)

        assert actions == []

    def test_pending_planning_preflight_does_not_setup_game(self, game_graph: Graph) -> None:
        block = _add_node(game_graph, kind=PresentationGameBlock, label="pending_game")
        ctx = Frame(graph=game_graph, cursor=block)._make_ctx()
        ctx.current_phase = ResolutionPhase.PLANNING

        assert provision_game_moves(block, ctx=ctx) is None
        assert block.game.phase is GamePhase.PENDING
        assert isinstance(block.game_handler, PresentationGameHandler)
        assert block.game_handler.presentation_calls == 1

    def test_stable_actions_are_not_reprojected_or_cleared(self, game_graph: Graph) -> None:
        block = _add_node(game_graph, kind=StableGameBlock, label="stable_game")
        block.game_handler.setup(block.game)
        authored_action = Action(
            graph=game_graph,
            predecessor_id=block.uid,
            successor_id=block.uid,
            label="Play the stable move",
            predicate="game_in_progress",
        )
        ctx = Frame(graph=game_graph, cursor=block)._make_ctx()

        actions = provision_game_moves(block, ctx=ctx)

        assert actions == []
        assert game_graph.get(authored_action.uid) is authored_action
        assert authored_action.available(ctx=ctx)

        block.game.result = GameResult.WIN

        terminal_ctx = Frame(graph=game_graph, cursor=block)._make_ctx()
        assert not authored_action.available(ctx=terminal_ctx)

    def test_typed_accepts_survives_graph_snapshot(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        action = Action(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=game_block.uid,
            accepts=PiecesAccepts(
                constraints=PieceConstraints(target_zone_ref="packet"),
            ),
        )

        restored = Graph.structure(game_graph.unstructure()).get(action.uid)

        assert isinstance(restored, Action)
        assert restored.accepts is not None
        assert restored.accepts.kind == "pieces"


class TestUpdateHandler:
    def test_prereqs_redirect_leaves_pending_game_uninitialized(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        intro = _add_node(game_graph, kind=Block, label="intro")
        redirected = _add_node(game_graph, kind=Block, label="redirected")
        entry = Action(
            graph=game_graph,
            predecessor_id=intro.uid,
            successor_id=game_block.uid,
            label="Enter game",
        )
        TraversableEdge(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=redirected.uid,
            trigger_phase=ResolutionPhase.PREREQS,
            label="redirect",
        )

        frame = Frame(graph=game_graph, cursor=intro)
        frame.resolve_choice(entry)

        assert frame.cursor is redirected
        assert game_block.game.phase is GamePhase.PENDING

    def test_accepted_entry_setups_pending_game_and_projects_moves(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        intro = _add_node(game_graph, kind=Block, label="intro")
        entry = Action(
            graph=game_graph,
            predecessor_id=intro.uid,
            successor_id=game_block.uid,
            label="Enter game",
        )

        frame = Frame(graph=game_graph, cursor=intro)
        frame.resolve_choice(entry)

        actions = [edge for edge in game_block.edges_out() if isinstance(edge, Action)]
        assert game_block.game.phase is GamePhase.READY
        assert {action.payload["move"] for action in actions} == {"win", "lose", "draw"}

    def test_ready_reentry_preserves_existing_game_state(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        game_block.game_handler.setup(game_block.game)
        game_block.game.score["player"] = 3
        action = Action(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=game_block.uid,
            payload={"move": "win"},
        )
        ctx = Frame(graph=game_graph, cursor=game_block)._make_ctx(
            incoming_edge=action,
            incoming_payload=action.payload,
        )

        process_game_move(game_block, ctx=ctx)

        assert game_block.game.score["player"] == 4

    def test_update_invalidates_game_namespace_after_resolution(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        game_block.game_handler.setup(game_block.game)
        action = Action(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=game_block.uid,
            payload={"move": "win"},
        )
        ctx = Frame(graph=game_graph, cursor=game_block)._make_ctx(
            incoming_edge=action,
            incoming_payload=action.payload,
        )

        assert ctx.get_ns(game_block)["game_won"] is False

        process_game_move(game_block, ctx=ctx)

        assert ctx.get_ns(game_block)["game_won"] is True

    def test_terminal_dynamic_move_leaves_stable_outcome_for_postreqs(
        self,
        game_graph: Graph,
    ) -> None:
        intro = _add_node(game_graph, kind=Block, label="intro")
        victory = _add_node(game_graph, kind=Block, label="victory")
        game_block = GameBlock.create_game_block(
            graph=game_graph,
            victory_dest=victory,
            label="game",
        )
        entry = Action(
            graph=game_graph,
            predecessor_id=intro.uid,
            successor_id=game_block.uid,
            label="Enter game",
        )
        frame = Frame(graph=game_graph, cursor=intro)

        frame.resolve_choice(entry)
        win_action = next(
            action
            for action in game_block.edges_out()
            if isinstance(action, Action) and action.payload == {"move": "win"}
        )
        frame.resolve_choice(win_action, choice_payload=win_action.payload)

        assert game_block.game.phase is GamePhase.TERMINAL
        assert not [
            action
            for action in game_block.edges_out()
            if isinstance(action, Action) and action.payload is not None
        ]
        assert frame.cursor is victory

    def test_ready_game_round_trip_does_not_setup_again(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        game_block.game_handler.setup(game_block.game)
        game_block.game.score["player"] = 3
        restored_graph = Graph.structure(game_graph.unstructure())
        restored = restored_graph.get(game_block.uid)
        assert isinstance(restored, GameBlock)
        ctx = Frame(graph=restored_graph, cursor=restored)._make_ctx()

        process_game_move(restored, ctx=ctx)

        assert restored.game.phase is GamePhase.READY
        assert restored.game.score["player"] == 3

    def test_move_processing_stores_results(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        game_block.game_handler.setup(game_block.game)

        action = Action(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=game_block.uid,
            payload={"move": "win"},
        )

        frame.resolve_choice(action)

        assert game_block.game.round == 1
        assert game_block.locals["round_result"] is RoundResult.WIN
        assert game_block.locals["game_result"] is GameResult.WIN
        assert game_block.locals["last_round"].player_move == "win"

    def test_move_ignored_without_payload(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        game_block.game_handler.setup(game_block.game)
        frame.selected_edge = Action(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=game_block.uid,
            payload=None,
        )

        process_game_move(game_block, ctx=ctx)

        assert "round_result" not in game_block.locals
        assert game_block.game.round == 0


class TestJournalHandler:
    def test_journal_projection_receives_the_live_phase_context(
        self,
        game_graph: Graph,
        game_block: GameBlock,
    ) -> None:
        ctx = make_ctx(make_frame(game_graph, game_block.uid))
        handler = ContextJournalHandler()
        game_block._game_handler = handler

        fragments = generate_game_journal(game_block, ctx=ctx)

        assert handler.received_ctx is ctx
        assert [fragment.content for fragment in fragments] == ["Context-aware journal."]

    def test_journal_generation_from_last_round(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        game_block.game_handler.setup(game_block.game)
        action = Action(
            graph=game_graph,
            predecessor_id=game_block.uid,
            successor_id=game_block.uid,
            payload={"move": "lose"},
        )
        ctx = frame._make_ctx(
            incoming_edge=action,
            incoming_payload=action.payload,
        )
        process_game_move(game_block, ctx=ctx)

        fragments = generate_game_journal(game_block, ctx=ctx)

        assert fragments
        assert any("You played" in fragment.content for fragment in fragments)
        assert any("lost this round" in fragment.content for fragment in fragments)
        assert any("Score" in fragment.content for fragment in fragments)

    def test_no_fragments_without_round(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        fragments = generate_game_journal(game_block, ctx=ctx)

        assert fragments == []


class TestContextHandler:
    def test_context_exports_predicates(self, game_graph: Graph, game_block: GameBlock):
        frame = make_frame(game_graph, game_block.uid)
        ctx = make_ctx(frame)

        game_block.game.result = GameResult.DRAW
        game_block.game.round = 2

        namespace = inject_game_context(game_block, ctx=ctx)

        assert namespace["game_draw"] is True
        assert namespace["game_won"] is False
        assert namespace["game_round"] == 2
