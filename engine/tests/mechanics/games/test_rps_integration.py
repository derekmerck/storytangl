from __future__ import annotations

"""Integration tests covering RPS gameplay through the VM pipeline."""

from tangl.core import Graph
from tangl.mechanics.games import GamePhase, GameResult, HasGame
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler, RpsMove
from tangl.story import Block
from tangl.mechanics.games.handlers import provision_game_moves
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge, get_visit_count


class RpsBlock(HasGame, Block):
    """Story block that embeds an RPS game."""


def _add_node(graph: Graph, *, kind, **attrs):
    return graph.add_node(kind=kind, **attrs)


def _make_ledger(graph: Graph, start_node: Block) -> Ledger:
    return Ledger.from_graph(graph=graph, entry_id=start_node.uid)


def _frame_ctx(frame: Frame):
    return frame._make_ctx()


def _resolve_edge(ledger: Ledger, edge: ChoiceEdge, *, choice_payload=None) -> None:
    ledger.resolve_choice(edge.uid, choice_payload=choice_payload)


def _journal_fragments(ledger: Ledger):
    return ledger.get_journal()


def test_complete_rps_game_to_victory():
    """Play through an RPS game and auto-exit on victory."""

    graph = Graph(label="rps_integration")

    intro = _add_node(graph, kind=Block, label="intro")
    victory = _add_node(graph, kind=Block, label="victory")
    defeat = _add_node(graph, kind=Block, label="defeat")

    game_block = RpsBlock.create_game_block(
        graph=graph,
        game_class=RpsGame,
        handler_class=RpsGameHandler,
        victory_dest=victory,
        defeat_dest=defeat,
        label="rps_game",
    )

    # Deterministic, fast resolution: first to 2, opponent always loses.
    game_block.game.scoring_strategy = "first_to_n"
    game_block.game.scoring_n = 2
    game_block.game.opponent_revision_strategy = "rps_throw"
    game_block.game_handler.setup(game_block.game)

    intro_to_game = ChoiceEdge(
        graph=graph,
        source_id=intro.uid,
        destination_id=game_block.uid,
        label="Play RPS",
    )

    ledger = _make_ledger(graph, intro)
    _resolve_edge(ledger, intro_to_game)

    assert ledger.cursor_id == game_block.uid
    assert game_block.game.phase is GamePhase.READY

    rounds_played = 0
    while game_block.game.result is GameResult.IN_PROCESS and rounds_played < 5:
        frame = ledger.get_frame()
        ctx = _frame_ctx(frame)
        actions = provision_game_moves(game_block, ctx=ctx)
        rock_action = next(
            action for action in actions if action.payload and action.payload.get("move") == RpsMove.ROCK
        )

        _resolve_edge(ledger, rock_action, choice_payload=rock_action.payload)

        rounds_played += 1

    assert rounds_played == 2
    assert game_block.game.result is GameResult.WIN
    assert ledger.cursor_id == victory.uid

    fragments = _journal_fragments(ledger)
    assert fragments
    assert any("You played" in getattr(fragment, "content", "") for fragment in fragments)

    game_visits = get_visit_count(game_block.uid, ledger.cursor_history)
    assert game_visits == 3
    assert ledger.turn == 3


def test_rps_game_to_defeat():
    """Verify defeat exits route to the configured destination."""

    graph = Graph(label="rps_integration_loss")

    intro = _add_node(graph, kind=Block, label="intro")
    victory = _add_node(graph, kind=Block, label="victory")
    defeat = _add_node(graph, kind=Block, label="defeat")

    game_block = RpsBlock.create_game_block(
        graph=graph,
        game_class=RpsGame,
        handler_class=RpsGameHandler,
        victory_dest=victory,
        defeat_dest=defeat,
        label="rps_game",
    )

    # Force immediate defeat: first to 1, opponent counters player's move.
    game_block.game.scoring_strategy = "first_to_n"
    game_block.game.scoring_n = 1
    game_block.game.opponent_revision_strategy = "rps_counter"
    game_block.game_handler.setup(game_block.game)

    intro_to_game = ChoiceEdge(
        graph=graph,
        source_id=intro.uid,
        destination_id=game_block.uid,
        label="Play RPS",
    )

    ledger = _make_ledger(graph, intro)
    _resolve_edge(ledger, intro_to_game)

    assert game_block.game.phase is GamePhase.READY

    frame = ledger.get_frame()
    ctx = _frame_ctx(frame)
    actions = provision_game_moves(game_block, ctx=ctx)
    selected_action = next(action for action in actions if action.payload and action.payload.get("move") == RpsMove.ROCK)

    _resolve_edge(ledger, selected_action, choice_payload=selected_action.payload)

    assert game_block.game.result is GameResult.LOSE
    assert ledger.cursor_id == defeat.uid

    game_visits = get_visit_count(game_block.uid, ledger.cursor_history)
    assert game_visits == 2
    assert ledger.turn == 3
