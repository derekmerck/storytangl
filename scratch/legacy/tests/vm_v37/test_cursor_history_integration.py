"""Integration coverage for cursor history during story traversal."""

from tangl.core import Graph, StreamRegistry
from tangl.story.episode.block import Block
from tangl.vm import ChoiceEdge, Ledger


def test_history_through_linear_story():
    """History tracks visits through a simple three-block story."""

    graph = Graph(label="linear_story")
    intro = graph.add_node(obj_cls=Block, label="intro")
    middle = graph.add_node(obj_cls=Block, label="middle")
    ending = graph.add_node(obj_cls=Block, label="end")

    intro_to_middle = ChoiceEdge(graph=graph, source_id=intro.uid, destination_id=middle.uid, label="Continue")
    middle_to_end = ChoiceEdge(graph=graph, source_id=middle.uid, destination_id=ending.uid, label="Finish")

    ledger = Ledger(graph=graph, cursor_id=intro.uid, records=StreamRegistry())
    ledger.push_snapshot()

    frame = ledger.get_frame()
    frame.resolve_choice(intro_to_middle)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.cursor_id == middle.uid
    assert ledger.cursor_history == [middle.uid]

    frame = ledger.get_frame()
    frame.resolve_choice(middle_to_end)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.cursor_id == ending.uid
    assert ledger.cursor_history == [middle.uid, ending.uid]
    assert ledger.turn == 2
    assert ledger.step == 2


def test_history_with_backtracking():
    """Backtracking still records each hop in order."""

    graph = Graph(label="backtrack")
    hub = graph.add_node(obj_cls=Block, label="hub")
    shop = graph.add_node(obj_cls=Block, label="shop")

    to_shop = ChoiceEdge(graph=graph, source_id=hub.uid, destination_id=shop.uid, label="Visit shop")
    back_to_hub = ChoiceEdge(graph=graph, source_id=shop.uid, destination_id=hub.uid, label="Leave shop")

    ledger = Ledger(graph=graph, cursor_id=hub.uid, records=StreamRegistry())
    ledger.push_snapshot()

    frame = ledger.get_frame()
    frame.resolve_choice(to_shop)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    frame = ledger.get_frame()
    frame.resolve_choice(back_to_hub)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.cursor_history == [shop.uid, hub.uid]
    assert ledger.cursor_id == hub.uid
    assert ledger.turn == 2
    assert ledger.step == 2


def test_history_with_game_self_loops():
    """Self-looping game states are recorded before exiting."""

    graph = Graph(label="game")
    game_block = graph.add_node(obj_cls=Block, label="rps_game")
    victory = graph.add_node(obj_cls=Block, label="victory")

    play_move = ChoiceEdge(graph=graph, source_id=game_block.uid, destination_id=game_block.uid, label="Play move")
    win_edge = ChoiceEdge(graph=graph, source_id=game_block.uid, destination_id=victory.uid, label="Victory!")

    ledger = Ledger(graph=graph, cursor_id=game_block.uid, records=StreamRegistry())
    ledger.push_snapshot()

    frame = ledger.get_frame()

    for _ in range(3):
        frame.resolve_choice(play_move)
        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step
        frame = ledger.get_frame()

    frame.resolve_choice(win_edge)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.cursor_history == [game_block.uid, game_block.uid, game_block.uid, victory.uid]
    assert ledger.turn == 2
    assert ledger.step == 4
