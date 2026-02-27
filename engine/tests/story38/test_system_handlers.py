"""Story38 journal handler contract tests."""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core38 import BehaviorRegistry, DispatchLayer, Graph, TemplateRegistry
from tangl.core38.runtime_op import Predicate
from tangl.story38 import StoryGraph38
from tangl.story38.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.story38.episode import Action, Block
from tangl.story38.system_handlers import (
    render_block,
    render_block_choices,
    render_block_content,
    render_block_media,
)
from tangl.vm38.dispatch import do_journal
from tangl.vm38 import Dependency, Requirement
from tangl.vm38.runtime.frame import PhaseCtx


def _ctx_with_ns(ns: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(get_ns=lambda _caller: dict(ns or {}))


def test_render_block_emits_content_media_and_choice_fragments() -> None:
    graph = Graph()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end", content="bye")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    fragments = render_block(caller=start, ctx=_ctx_with_ns({"name": "Joe"}))
    assert fragments is not None
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "Hello Joe"
    assert any(isinstance(fragment, MediaFragment) for fragment in fragments)

    choices = [fragment for fragment in fragments if isinstance(fragment, ChoiceFragment)]
    assert len(choices) == 1
    assert choices[0].available is True
    assert choices[0].unavailable_reason is None


def test_render_block_choice_unavailable_reason_missing_successor() -> None:
    graph = Graph()
    start = Block(label="start")
    graph.add(start)
    graph.add(Action(predecessor_id=start.uid, text="Broken"))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_successor"
    assert choice.blockers == [{"type": "edge", "reason": "missing_successor"}]


def test_render_block_choice_missing_successor_uses_preview_blockers_when_dependency_exists() -> None:
    graph = StoryGraph38()
    start = Block(label="start")
    graph.add(start)
    action = Action(predecessor_id=start.uid, text="Broken")
    graph.add(action)
    requirement = Requirement(has_identifier="missing", hard_requirement=True)
    graph.add(Dependency(predecessor_id=action.uid, label="destination", requirement=requirement))
    # No templates available for resolution.
    graph.factory = TemplateRegistry(label="empty")

    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    fragments = render_block(caller=start, ctx=ctx)
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_successor"
    assert choice.blockers is not None
    assert choice.blockers[0]["type"] == "provision"


def test_render_block_choice_unavailable_reason_missing_dependency() -> None:
    graph = Graph()
    start = Block(label="start")
    locked = Block(label="locked", availability=[Predicate(expr="False")])
    graph.add(start)
    graph.add(locked)
    graph.add(Action(predecessor_id=start.uid, successor_id=locked.uid, text="Try door"))
    requirement = Requirement(has_label="key")
    requirement.resolution_reason = "no_offers"
    requirement.resolution_meta = {"alternatives": []}
    graph.add(Dependency(predecessor_id=locked.uid, requirement=requirement))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_dependency"
    assert choice.blockers is not None
    assert choice.blockers[0]["type"] == "dependency"
    assert choice.blockers[0]["resolution_reason"] == "no_offers"
    assert choice.blockers[0]["resolution_meta"] == {"alternatives": []}


def test_render_block_choice_hard_dependency_blocks_even_when_guard_is_true() -> None:
    graph = Graph()
    start = Block(label="start")
    reachable = Block(label="reachable")
    graph.add(start)
    graph.add(reachable)
    graph.add(Action(predecessor_id=start.uid, successor_id=reachable.uid, text="Open"))
    requirement = Requirement(has_label="key", hard_requirement=True)
    requirement.resolution_reason = "no_offers"
    graph.add(Dependency(predecessor_id=reachable.uid, requirement=requirement))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_dependency"


def test_render_block_choice_unavailable_reason_guard_failed() -> None:
    graph = Graph()
    start = Block(label="start")
    locked = Block(label="locked", availability=[Predicate(expr="False")])
    graph.add(start)
    graph.add(locked)
    graph.add(Action(predecessor_id=start.uid, successor_id=locked.uid, text="Try door"))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "guard_failed_or_unavailable"


def test_render_block_emits_choice_payload_accepts_and_ui_hints() -> None:
    graph = Graph()
    start = Block(label="start")
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(
        Action(
            predecessor_id=start.uid,
            successor_id=end.uid,
            text="Pick a color",
            accepts={"type": "string", "enum": ["red", "blue", "green"]},
            ui_hints={"widget": "select", "framework": "vuetify"},
        )
    )

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.accepts == {"type": "string", "enum": ["red", "blue", "green"]}
    assert choice.ui_hints == {"widget": "select", "framework": "vuetify"}


def test_render_block_compatibility_facade_merges_split_handlers() -> None:
    graph = Graph()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    ctx = _ctx_with_ns({"name": "Joe"})
    content = render_block_content(caller=start, ctx=ctx)
    media = render_block_media(caller=start, ctx=ctx)
    choices = render_block_choices(caller=start, ctx=ctx)

    fragments = render_block(caller=start, ctx=ctx)
    assert fragments is not None
    expected_len = (
        (1 if content is not None else 0)
        + (len(media) if media else 0)
        + (len(choices) if choices else 0)
    )
    assert len(fragments) == expected_len
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "Hello Joe"
    assert any(isinstance(fragment, MediaFragment) for fragment in fragments)
    assert any(isinstance(fragment, ChoiceFragment) for fragment in fragments)


def test_dispatch_journal_allows_custom_handler_injection() -> None:
    graph = StoryGraph38()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    custom_registry = BehaviorRegistry(
        label="custom.story.journal",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )

    def _custom_overlay(*, caller, ctx, **_kw):
        if isinstance(caller, Block):
            return ContentFragment(content="overlay", source_id=caller.uid)
        return None
    custom_registry.register(_custom_overlay, task="render_journal", priority=0)

    graph.world = SimpleNamespace(get_authorities=lambda: [custom_registry])
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    ctx._ns_cache[start.uid] = {"name": "Joe"}  # bypass gather_ns wiring for focused journal test

    fragments = do_journal(start, ctx=ctx)
    assert isinstance(fragments, list)

    contents = [fragment.content for fragment in fragments if isinstance(fragment, ContentFragment)]
    assert "overlay" in contents
    assert "Hello Joe" in contents


def test_render_block_content_includes_graph_locals_from_phase_ctx_tail_layer() -> None:
    graph = StoryGraph38(locals={"gold": 10})
    start = Block(label="start", content="Gold: {gold}")
    graph.add(start)
    graph.initial_cursor_id = start.uid
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)

    fragments = do_journal(start, ctx=ctx)
    if isinstance(fragments, ContentFragment):
        content = fragments
    else:
        assert isinstance(fragments, list)
        content = next(fragment for fragment in fragments if isinstance(fragment, ContentFragment))
    assert content.content == "Gold: 10"
