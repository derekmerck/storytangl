from __future__ import annotations

"""Integration tests covering RPS gameplay through the VM pipeline."""

from tangl.core import Graph, StreamRegistry, BaseFragment
from tangl.mechanics.games import GamePhase, GameResult, HasGame
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler, RpsMove
from tangl.story import Block
from tangl.mechanics.games.handlers import provision_game_moves
from tangl.vm import ChoiceEdge, Ledger, get_visit_count


class RpsBlock(HasGame, Block):
    """Story block that embeds an RPS game."""


def _make_ledger(graph: Graph, start_node: Block) -> Ledger:
    ledger = Ledger(graph=graph, cursor_id=start_node.uid, records=StreamRegistry())
    ledger.cursor_history.append(start_node.uid)
    return ledger


def test_complete_rps_game_to_victory():
    """Play through an RPS game and auto-exit on victory."""

    graph = Graph(label="rps_integration")

    intro = graph.add_node(obj_cls=Block, label="intro")
    victory = graph.add_node(obj_cls=Block, label="victory")
    defeat = graph.add_node(obj_cls=Block, label="defeat")

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

    intro_to_game = ChoiceEdge(
        graph=graph,
        source_id=intro.uid,
        destination_id=game_block.uid,
        label="Play RPS",
    )

    ledger = _make_ledger(graph, intro)
    frame = ledger.get_frame()
    frame.selected_edge = intro_to_game
    frame.resolve_choice(intro_to_game)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.cursor_id == game_block.uid
    assert game_block.game.phase is GamePhase.READY

    rounds_played = 0
    while game_block.game.result is GameResult.IN_PROCESS and rounds_played < 5:
        frame = ledger.get_frame()
        actions = provision_game_moves(game_block, ctx=frame.context)
        rock_action = next(
            action for action in actions if action.payload and action.payload.get("move") == RpsMove.ROCK
        )

        frame.selected_edge = rock_action
        frame.resolve_choice(rock_action)
        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step

        rounds_played += 1

    assert rounds_played == 2
    assert game_block.game.result is GameResult.WIN
    assert ledger.cursor_id == victory.uid

    fragments = list(ledger.records.find_all(is_instance=BaseFragment))
    assert fragments
    assert any("You played" in fragment.content for fragment in fragments)

    game_visits = get_visit_count(game_block.uid, ledger.cursor_history)
    assert game_visits == 3
    assert ledger.turn == 3


def test_rps_game_to_defeat():
    """Verify defeat exits route to the configured destination."""

    graph = Graph(label="rps_integration_loss")

    intro = graph.add_node(obj_cls=Block, label="intro")
    victory = graph.add_node(obj_cls=Block, label="victory")
    defeat = graph.add_node(obj_cls=Block, label="defeat")

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

    intro_to_game = ChoiceEdge(
        graph=graph,
        source_id=intro.uid,
        destination_id=game_block.uid,
        label="Play RPS",
    )

    ledger = _make_ledger(graph, intro)
    frame = ledger.get_frame()
    frame.selected_edge = intro_to_game
    frame.resolve_choice(intro_to_game)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert game_block.game.phase is GamePhase.READY

    frame = ledger.get_frame()
    actions = provision_game_moves(game_block, ctx=frame.context)
    selected_action = next(action for action in actions if action.payload and action.payload.get("move") == RpsMove.ROCK)

    frame.selected_edge = selected_action
    frame.resolve_choice(selected_action)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert game_block.game.result is GameResult.LOSE
    assert ledger.cursor_id == defeat.uid

    game_visits = get_visit_count(game_block.uid, ledger.cursor_history)
    assert game_visits == 2
    assert ledger.turn == 3
