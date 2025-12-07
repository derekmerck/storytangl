from __future__ import annotations

from tangl.vm import Frame, ResolutionPhase as P
from tangl.vm.dispatch import vm_dispatch
from tangl.story.dispatch import story_dispatch
from tangl.story.episode import Block
from tangl.story.mechanics.games import HasGame
from tangl.story.story_graph import StoryGraph
from tangl.mechanics.games import Game
from tangl.journal.content import ContentFragment


class TestGame(Game):
    """Minimal test game for journal generation."""

    def matches(self, **_: object) -> bool:  # pragma: no cover - helper for dispatch
        return True


class TestGameBlock(Block, HasGame):
    """Block embedding a test game."""


@vm_dispatch.register(task="generate_journal", caller=TestGame)
def generate_test_game_journal(game: TestGame, *, ctx, **kwargs):
    return "Game content"


def test_game_content_wins_over_block_content() -> None:
    """Game gather_content should run before block gather_content."""

    graph = StoryGraph(label="test")
    game = TestGame()
    block = TestGameBlock(graph=graph, label="game_block", content="Block content")
    object.__setattr__(block, "_game", game)

    frame = Frame(graph=graph, cursor_id=block.uid)

    with frame.context._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="gather_content", ctx=frame.context)
        content = None
        for receipt in receipts:
            if receipt.result is not None:
                content = receipt.result
                break

    assert content == "Game content"


def test_block_content_used_when_no_game() -> None:
    """Block gather_content runs when no game is attached."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block", content="Block content")

    frame = Frame(graph=graph, cursor_id=block.uid)

    with frame.context._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="gather_content", ctx=frame.context)
        content = None
        for receipt in receipts:
            if receipt.result is not None:
                content = receipt.result
                break

    assert content == "Block content"


def test_empty_block_returns_none() -> None:
    """Empty block content should return None to allow fallbacks."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block", content="")

    frame = Frame(graph=graph, cursor_id=block.uid)

    with frame.context._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="gather_content", ctx=frame.context)
        content = None
        for receipt in receipts:
            if receipt.result is not None:
                content = receipt.result
                break

    assert content is None


def test_content_stored_in_context() -> None:
    """compose_block_journal caches the selected content on the context."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block", content="Inline content")

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    assert isinstance(frame.context.current_content, list)
    assert any(
        isinstance(fragment, ContentFragment)
        and fragment.content == "Inline content"
        for fragment in frame.context.current_content
    )
    assert any(
        isinstance(fragment, ContentFragment) and fragment.content == "Inline content"
        for fragment in fragments
    )
