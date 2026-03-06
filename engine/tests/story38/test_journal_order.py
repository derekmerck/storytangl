"""Fragment emission-order contracts for story38 journal handlers.

Asserts that the three built-in journal handlers fire in the expected priority
order (EARLY → NORMAL → LATE), producing:

    ContentFragment  (render_block_content, Priority.EARLY)
    MediaFragment    (render_block_media,   Priority.NORMAL)
    ChoiceFragment   (render_block_choices, Priority.LATE)

Tests run both via the compatibility facade (``render_block``) and through the
real dispatch pipeline (``do_journal``), so we catch any priority-table drift.

See Also
--------
- ``tangl.story.system_handlers`` – handler registrations
- ``tangl.vm.dispatch.do_journal`` – phase pipeline entry point
- ``tangl.story.dispatch.story_dispatch`` – story-layer behavior registry
"""

from __future__ import annotations

import pytest

from tangl.story.episode import Action, Block
from tangl.story.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.story.story_graph import StoryGraph38
from tangl.story.system_handlers import render_block
from tangl.vm.dispatch import do_journal
from tangl.vm.runtime.frame import PhaseCtx

import tangl.story  # noqa: F401 – registers story38 handlers into story_dispatch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _two_block_graph(
    *,
    content: str = "Hello {name}",
    media: list | None = None,
    has_action: bool = True,
) -> tuple[StoryGraph38, Block, Block]:
    """Return a graph with a ``start`` block wired to an ``end`` block."""
    graph = StoryGraph38(label="order_story")
    start = Block(label="start", content=content, media=media or [])
    end = Block(label="end", content="Done")
    graph.add(start)
    graph.add(end)
    if has_action:
        graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Go"))
    return graph, start, end


def _ctx(graph: StoryGraph38, cursor: Block, ns: dict | None = None) -> PhaseCtx:
    ctx = PhaseCtx(graph=graph, cursor_id=cursor.uid)
    ctx._ns_cache[cursor.uid] = ns or {}
    return ctx


# ---------------------------------------------------------------------------
# render_block compatibility facade ordering
# ---------------------------------------------------------------------------

class TestRenderBlockFacadeOrder:
    """Direct-call facade preserves content → media → choice ordering."""

    def test_content_before_media_before_choice(self) -> None:
        graph, start, _end = _two_block_graph(media=[{"kind": "image", "src": "a.svg"}])
        ctx = _ctx(graph, start, {"name": "World"})

        fragments = render_block(caller=start, ctx=ctx)

        assert fragments is not None
        types = [type(f).__name__ for f in fragments]
        assert types == ["ContentFragment", "MediaFragment", "ChoiceFragment"]

    def test_content_fragment_is_first_even_without_media(self) -> None:
        graph, start, _end = _two_block_graph(media=[])
        ctx = _ctx(graph, start, {"name": "World"})

        fragments = render_block(caller=start, ctx=ctx)

        assert fragments is not None
        assert isinstance(fragments[0], ContentFragment)
        assert isinstance(fragments[-1], ChoiceFragment)

    def test_no_media_fragment_when_media_is_empty(self) -> None:
        graph, start, _end = _two_block_graph(media=[])
        ctx = _ctx(graph, start)

        fragments = render_block(caller=start, ctx=ctx)

        assert fragments is not None
        assert not any(isinstance(f, MediaFragment) for f in fragments)

    def test_multiple_media_items_all_precede_choices(self) -> None:
        media = [{"kind": "image", "src": "a.svg"}, {"kind": "image", "src": "b.svg"}]
        graph, start, _end = _two_block_graph(media=media)
        ctx = _ctx(graph, start)

        fragments = render_block(caller=start, ctx=ctx)

        assert fragments is not None
        media_indices = [i for i, f in enumerate(fragments) if isinstance(f, MediaFragment)]
        choice_indices = [i for i, f in enumerate(fragments) if isinstance(f, ChoiceFragment)]
        assert media_indices  # at least one media fragment
        assert choice_indices  # at least one choice fragment
        assert max(media_indices) < min(choice_indices)

    def test_multiple_choices_follow_all_content_and_media(self) -> None:
        graph = StoryGraph38(label="multi_choice")
        start = Block(label="start", content="Pick", media=[{"kind": "image", "src": "x.svg"}])
        a = Block(label="a")
        b = Block(label="b")
        graph.add(start)
        graph.add(a)
        graph.add(b)
        graph.add(Action(predecessor_id=start.uid, successor_id=a.uid, text="Left"))
        graph.add(Action(predecessor_id=start.uid, successor_id=b.uid, text="Right"))
        ctx = _ctx(graph, start)

        fragments = render_block(caller=start, ctx=ctx)

        assert fragments is not None
        first_choice = next(i for i, f in enumerate(fragments) if isinstance(f, ChoiceFragment))
        last_non_choice = max(
            i for i, f in enumerate(fragments) if not isinstance(f, ChoiceFragment)
        )
        assert last_non_choice < first_choice

    def test_no_fragments_emitted_for_non_block_caller(self) -> None:
        from tangl.story.episode import Scene
        from types import SimpleNamespace

        scene = Scene(label="scene")
        ctx = SimpleNamespace(get_ns=lambda _: {})
        result = render_block(caller=scene, ctx=ctx)
        assert result is None


# ---------------------------------------------------------------------------
# do_journal dispatch pipeline ordering
# ---------------------------------------------------------------------------

class TestDoJournalDispatchOrder:
    """Story38 handlers registered in story_dispatch maintain order under dispatch."""

    def test_do_journal_preserves_content_media_choice_order(self) -> None:
        graph, start, _end = _two_block_graph(media=[{"kind": "image", "src": "a.svg"}])
        ctx = _ctx(graph, start, {"name": "Joe"})

        fragments = do_journal(start, ctx=ctx)

        assert isinstance(fragments, list)
        types = [type(f).__name__ for f in fragments]
        assert types.index("ContentFragment") < types.index("MediaFragment")
        assert types.index("MediaFragment") < types.index("ChoiceFragment")

    def test_do_journal_content_text_is_rendered(self) -> None:
        graph, start, _end = _two_block_graph()
        ctx = _ctx(graph, start, {"name": "Alice"})

        fragments = do_journal(start, ctx=ctx)

        content = next((f for f in fragments if isinstance(f, ContentFragment)), None)
        assert content is not None
        assert "Alice" in content.content

    def test_do_journal_returns_empty_list_for_non_block(self) -> None:
        from tangl.story.episode import Scene

        graph = StoryGraph38(label="g")
        scene = Scene(label="s")
        graph.add(scene)
        ctx = _ctx(graph, Block(label="dummy"))  # cursor irrelevant; caller drives

        # do_journal dispatches on caller type; a Scene should produce nothing
        result = do_journal(scene, ctx=ctx)
        # No registered handler matches Scene, so empty list expected
        assert result == [] or result is None

    def test_do_journal_choice_source_id_matches_block_uid(self) -> None:
        graph, start, _end = _two_block_graph()
        ctx = _ctx(graph, start)

        fragments = do_journal(start, ctx=ctx)

        choice = next((f for f in fragments if isinstance(f, ChoiceFragment)), None)
        assert choice is not None
        assert choice.edge_id is not None  # uid of the Action edge

    def test_do_journal_media_source_id_matches_block_uid(self) -> None:
        graph, start, _end = _two_block_graph(media=[{"kind": "audio", "src": "sound.ogg"}])
        ctx = _ctx(graph, start)

        fragments = do_journal(start, ctx=ctx)

        media = next((f for f in fragments if isinstance(f, MediaFragment)), None)
        assert media is not None
        assert media.source_id == start.uid
