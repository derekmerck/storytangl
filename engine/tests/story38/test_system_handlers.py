"""Story38 journal handler contract tests."""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core38 import Graph
from tangl.core38.runtime_op import Predicate
from tangl.story38.episode import Action, Block
from tangl.story38.system_handlers import render_block
from tangl.vm38 import ChoiceFragment, ContentFragment, Dependency, MediaFragment


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


def test_render_block_choice_unavailable_reason_missing_dependency() -> None:
    graph = Graph()
    start = Block(label="start")
    locked = Block(label="locked", availability=[Predicate(expr="False")])
    graph.add(start)
    graph.add(locked)
    graph.add(Action(predecessor_id=start.uid, successor_id=locked.uid, text="Try door"))
    graph.add(Dependency(predecessor_id=locked.uid, requirement={"has_label": "key"}))

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
