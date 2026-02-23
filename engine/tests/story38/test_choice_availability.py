"""Choice availability and blocker-diagnostics contract tests for story38.

Covers the full availability decision surface visible to the renderer:

- Predicate-guarded choices (simple and compound expressions)
- Dependency-blocked choices (hard and soft; resolved and unresolved)
- Concept gating via Role/Setting satisfaction state
- ``_choice_unavailable_reason`` reason-code taxonomy
- ``_choice_blockers`` structured diagnostic output
- Available vs. unavailable coexistence in the same menu

The tests operate at the fragment level (``render_block_choices``) and
through the full ``render_block`` facade so both call-paths are exercised.

See Also
--------
- ``tangl.story38.system_handlers`` – ``_choice_unavailable_reason``, ``_choice_blockers``
- ``tangl.vm38`` – ``Requirement``, ``Dependency``
- ``tangl.core38.runtime_op`` – ``Predicate``
- ``tangl.story38.concepts`` – ``Role``, ``Setting``
"""

from __future__ import annotations

import pytest

from tangl.core38 import Graph, Selector
from tangl.core38.runtime_op import Predicate
from tangl.story38.concepts import Actor, Location, Role, Setting
from tangl.story38.episode import Action, Block, Scene
from tangl.story38.fragments import ChoiceFragment, ContentFragment
from tangl.story38.story_graph import StoryGraph38
from tangl.story38.system_handlers import render_block, render_block_choices
from tangl.vm38 import Dependency, Requirement

import tangl.story38  # noqa: F401 – register story38 handlers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_ctx(ns: dict | None = None):
    """Minimal ctx stub sufficient for availability checks."""
    from types import SimpleNamespace
    return SimpleNamespace(get_ns=lambda _caller: dict(ns or {}))


def _full_ctx(graph: StoryGraph38, cursor: Block, ns: dict | None = None):
    from tangl.vm38.runtime.frame import PhaseCtx
    ctx = PhaseCtx(graph=graph, cursor_id=cursor.uid)
    ctx._ns_cache[cursor.uid] = ns or {}
    return ctx


def _graph_with_choice(
    *,
    guard_expr: str | None = None,
    dependency: Requirement | None = None,
) -> tuple[Graph, Block, Block, Action]:
    """Return (graph, start, end, action) with optional guard/dependency on end."""
    graph = Graph()
    start = Block(label="start", content="Crossroads")
    end = Block(label="end", content="Destination")
    graph.add(start)
    graph.add(end)

    if guard_expr is not None:
        end.availability = [Predicate(expr=guard_expr)]

    action = Action(predecessor_id=start.uid, successor_id=end.uid, text="Go")
    graph.add(action)

    if dependency is not None:
        dep = Dependency(predecessor_id=end.uid, requirement=dependency)
        graph.add(dep)

    return graph, start, end, action


# ---------------------------------------------------------------------------
# Available choices
# ---------------------------------------------------------------------------

class TestAvailableChoices:
    def test_unconditional_choice_is_available(self) -> None:
        graph, start, _end, _action = _graph_with_choice()
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and len(fragments) == 1
        assert fragments[0].available is True
        assert fragments[0].unavailable_reason is None
        assert fragments[0].blockers is None

    def test_satisfied_predicate_makes_choice_available(self) -> None:
        graph, start, _end, _action = _graph_with_choice(guard_expr="gold > 3")
        ctx = _simple_ctx({"gold": 5})

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is True

    def test_choice_text_is_forwarded(self) -> None:
        graph, start, _end, _action = _graph_with_choice()
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].text == "Go"

    def test_action_with_accepts_and_ui_hints_forwarded(self) -> None:
        graph = Graph()
        start = Block(label="start")
        end = Block(label="end")
        graph.add(start)
        graph.add(end)
        action = Action(
            predecessor_id=start.uid,
            successor_id=end.uid,
            text="Pick",
            accepts={"type": "string", "enum": ["a", "b"]},
            ui_hints={"widget": "radio"},
        )
        graph.add(action)
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments
        assert fragments[0].accepts == {"type": "string", "enum": ["a", "b"]}
        assert fragments[0].ui_hints == {"widget": "radio"}


# ---------------------------------------------------------------------------
# Predicate-guarded (guard_failed_or_unavailable)
# ---------------------------------------------------------------------------

class TestPredicateGating:
    def test_failing_predicate_marks_choice_unavailable(self) -> None:
        graph, start, _end, _action = _graph_with_choice(guard_expr="gold > 10")
        ctx = _simple_ctx({"gold": 2})

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is False

    def test_failing_predicate_reason_code(self) -> None:
        graph, start, _end, _action = _graph_with_choice(guard_expr="has_key")
        ctx = _simple_ctx({"has_key": False})

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].unavailable_reason == "guard_failed_or_unavailable"

    def test_failing_predicate_blocker_type_is_edge(self) -> None:
        graph, start, _end, _action = _graph_with_choice(guard_expr="False")
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].blockers is not None
        assert any(b["type"] == "edge" for b in fragments[0].blockers)

    def test_compound_and_predicate_fails_when_any_term_false(self) -> None:
        graph, start, _end, _action = _graph_with_choice(guard_expr="gold > 3 and has_key")
        ctx = _simple_ctx({"gold": 5, "has_key": False})

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is False

    def test_compound_or_predicate_passes_when_any_term_true(self) -> None:
        graph, start, _end, _action = _graph_with_choice(guard_expr="gold > 3 or has_key")
        ctx = _simple_ctx({"gold": 5, "has_key": False})

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is True


# ---------------------------------------------------------------------------
# Missing successor
# ---------------------------------------------------------------------------

class TestMissingSuccessor:
    def test_dangling_action_reason_is_missing_successor(self) -> None:
        graph = Graph()
        start = Block(label="start")
        graph.add(start)
        graph.add(Action(predecessor_id=start.uid, text="Broken"))  # no successor
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is False
        assert fragments[0].unavailable_reason == "missing_successor"
        assert fragments[0].blockers == [{"type": "edge", "reason": "missing_successor"}]


# ---------------------------------------------------------------------------
# Dependency-blocked (missing_dependency)
# ---------------------------------------------------------------------------

class TestDependencyGating:
    def test_unresolved_hard_dependency_blocks_choice(self) -> None:
        req = Requirement(has_label="key", hard_requirement=True)
        req.resolution_reason = "no_offers"
        req.resolution_meta = {"alternatives": []}
        graph, start, _end, _action = _graph_with_choice(dependency=req)
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is False
        assert fragments[0].unavailable_reason == "missing_dependency"

    def test_dependency_blocker_carries_resolution_metadata(self) -> None:
        req = Requirement(has_label="key", hard_requirement=True)
        req.resolution_reason = "no_offers"
        req.resolution_meta = {"tried": ["template_provisioner"]}
        graph, start, _end, _action = _graph_with_choice(dependency=req)
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments
        dep_blockers = [b for b in (fragments[0].blockers or []) if b.get("type") == "dependency"]
        assert dep_blockers
        assert dep_blockers[0]["resolution_reason"] == "no_offers"
        assert dep_blockers[0]["resolution_meta"] == {"tried": ["template_provisioner"]}

    def test_satisfied_dependency_does_not_block(self) -> None:
        req = Requirement(has_label="key", hard_requirement=True)
        # No resolution_reason set → dependency is not in the unsatisfied set
        graph, start, end, _action = _graph_with_choice()
        # Wire a satisfied dep directly
        dep = Dependency(predecessor_id=end.uid, requirement=req)
        graph.add(dep)
        dep.requirement.provider_id = end.uid  # mark as resolved without setter mutation
        ctx = _simple_ctx()

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is True


# ---------------------------------------------------------------------------
# Concept gating via Role/Setting namespace
# ---------------------------------------------------------------------------

class TestConceptGating:
    """Choices guarded on Role/Setting namespace values."""

    def _guarded_graph(self, guard_expr: str) -> tuple[StoryGraph38, Block, Block, Actor]:
        graph = StoryGraph38(label="concept_story")
        scene = Scene(label="scene")
        start = Block(label="start", content="Hello {host_name}")
        end = Block(label="end", availability=[Predicate(expr=guard_expr)])
        actor = Actor(label="guard", name="Joe")

        graph.add(scene)
        graph.add(start)
        graph.add(end)
        graph.add(actor)
        scene.add_child(start)
        scene.add_child(end)

        role = Role(
            label="host",
            predecessor_id=scene.uid,
            requirement=Requirement(has_kind=Actor, hard_requirement=False),
        )
        graph.add(role)
        role.set_provider(actor)

        graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Greet host"))
        return graph, start, end, actor

    def test_choice_available_when_role_satisfies_guard(self) -> None:
        graph, start, _end, actor = self._guarded_graph("'host' in roles")
        ctx = _full_ctx(graph, start)

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and fragments[0].available is True

    def test_choice_unavailable_when_guard_references_missing_role(self) -> None:
        graph, start, _end, _actor = self._guarded_graph("'wizard' in roles")
        ctx = _full_ctx(graph, start)

        fragments = render_block_choices(caller=start, ctx=ctx)

        # roles namespace won't have 'wizard', so the guard fails
        assert fragments and fragments[0].available is False


# ---------------------------------------------------------------------------
# Mixed: available and unavailable in the same menu
# ---------------------------------------------------------------------------

class TestMixedMenu:
    def test_available_and_unavailable_choices_coexist(self) -> None:
        graph = Graph()
        start = Block(label="start")
        open_dest = Block(label="open_dest")
        locked_dest = Block(label="locked_dest", availability=[Predicate(expr="has_key")])
        graph.add(start)
        graph.add(open_dest)
        graph.add(locked_dest)
        graph.add(Action(predecessor_id=start.uid, successor_id=open_dest.uid, text="Open door"))
        graph.add(Action(predecessor_id=start.uid, successor_id=locked_dest.uid, text="Secret door"))
        ctx = _simple_ctx({"has_key": False})

        fragments = render_block_choices(caller=start, ctx=ctx)

        assert fragments and len(fragments) == 2
        available = [f for f in fragments if f.available]
        unavailable = [f for f in fragments if not f.available]
        assert len(available) == 1
        assert len(unavailable) == 1
        assert available[0].text == "Open door"
        assert unavailable[0].text == "Secret door"

    def test_render_block_includes_all_choice_fragments(self) -> None:
        graph = Graph()
        start = Block(label="start", content="Choose")
        a = Block(label="a")
        b = Block(label="b", availability=[Predicate(expr="False")])
        graph.add(start)
        graph.add(a)
        graph.add(b)
        graph.add(Action(predecessor_id=start.uid, successor_id=a.uid, text="Go A"))
        graph.add(Action(predecessor_id=start.uid, successor_id=b.uid, text="Go B"))
        ctx = _simple_ctx()

        all_fragments = render_block(caller=start, ctx=ctx)

        assert all_fragments is not None
        choices = [f for f in all_fragments if isinstance(f, ChoiceFragment)]
        assert len(choices) == 2
        assert sum(1 for c in choices if c.available) == 1
        assert sum(1 for c in choices if not c.available) == 1
