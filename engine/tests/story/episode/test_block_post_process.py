"""Tests for post-processing block content."""

from tangl.vm import Context
from tangl.story.episode import Block
from tangl.story.story_graph import StoryGraph
from tangl.journal.content import ContentFragment
from tangl.journal.discourse import AttributedFragment


def _first_result(receipts):
    for receipt in receipts:
        if receipt.result is not None:
            return receipt.result
    return None


def test_string_without_dialog_wraps_in_fragment() -> None:
    """Plain strings become content fragments during post-processing."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block")

    ctx = Context(graph=graph, cursor_id=block.uid)
    ctx.set_current_content("Plain text")

    from tangl.story.dispatch import story_dispatch

    with ctx._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="post_process_content", ctx=ctx)

    result = _first_result(receipts)

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], ContentFragment)
    assert result[0].content == "Plain text"


def test_string_with_dialog_parses() -> None:
    """Dialog microblocks in strings are parsed into attributed fragments."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block")

    ctx = Context(graph=graph, cursor_id=block.uid)
    ctx.set_current_content("> [!dialog] Guard\n> Halt!")

    from tangl.story.dispatch import story_dispatch

    with ctx._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="post_process_content", ctx=ctx)

    result = _first_result(receipts)

    assert isinstance(result, list)

    dialog_frags = [fragment for fragment in result if isinstance(fragment, AttributedFragment)]
    assert dialog_frags
    assert dialog_frags[0].content == "Halt!"


def test_fragments_pass_through() -> None:
    """Existing fragments pass through unchanged."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block")

    fragments = [
        ContentFragment(content="test1"),
        ContentFragment(content="test2"),
    ]

    ctx = Context(graph=graph, cursor_id=block.uid)
    ctx.set_current_content(fragments)

    from tangl.story.dispatch import story_dispatch

    with ctx._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="post_process_content", ctx=ctx)

    result = _first_result(receipts)

    assert result == fragments


def test_none_returns_none() -> None:
    """None content returns None for post-processing."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block")

    ctx = Context(graph=graph, cursor_id=block.uid)
    ctx.set_current_content(None)

    from tangl.story.dispatch import story_dispatch

    with ctx._fresh_call_receipts():
        receipts = story_dispatch.dispatch(block, task="post_process_content", ctx=ctx)

    result = _first_result(receipts)

    assert result is None
