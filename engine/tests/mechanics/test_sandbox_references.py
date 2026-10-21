"""Sandbox reference precedence, live graph semantics and bounded path work."""

from __future__ import annotations

import pytest

from tangl.core import Entity, GraphItem, Node, Singleton, Token
from tangl.mechanics.sandbox import SandboxLocation
from tangl.mechanics.sandbox.handlers import _resolve_ref
from tangl.story import Block, Scene, StoryGraph
from tangl.vm import TraversableNode


class AliasBlock(Block):
    """A custom matching policy need not use the label as its path tail."""

    def has_path(self, pattern: str) -> bool:
        return pattern == "logical.alias" or super().has_path(pattern)


class IdentifierOnlyBlock(Block):
    def has_path(self, pattern: str) -> bool:
        return False


class TraversableSuggestion(Singleton):
    """A token's advertised kind is not its Python instance type."""

    def has_kind(self, kind: type[Entity]) -> bool:
        return kind is TraversableNode or super().has_kind(kind)


@pytest.mark.parametrize("reference", [
    "scope.target", "target", "dotted.target", "uuid", "shortcode",
    "scope.targ?t", "scope.[t]arget", "scope.t*", "missing", "SCOPE.TARGET",
])
def test_reference_paths_identifiers_globs_and_missing(reference: str) -> None:
    graph = StoryGraph()
    scope = Scene(label="scope", registry=graph)
    hub = SandboxLocation(label="hub", registry=graph)
    target = Block(label="target", registry=graph)
    dotted = Block(label="dotted.target", registry=graph)
    scope.add_child(hub)
    scope.add_child(target)
    expected = target
    if reference == "uuid":
        reference = str(target.uid)
        # This str-only seam does not coerce UUID spellings; shortcode is the
        # supported textual identity fallback. Preserve that existing behavior.
        expected = None
    elif reference == "shortcode":
        reference = target.shortcode()
    elif reference == "dotted.target":
        expected = dotted
    elif reference in ("missing", "SCOPE.TARGET"):
        # Use the platform's authoritative fnmatch behavior, not a new case policy.
        expected = target if target.has_path(reference) else None
    assert _resolve_ref(hub, reference, kind=Block) is expected


def test_path_precedes_identifier_and_identifier_precedes_scoped_fallback() -> None:
    graph = StoryGraph()
    scope = Scene(label="scope", registry=graph)
    hub = SandboxLocation(label="hub", sandbox_scope="scope", registry=graph)
    scope.add_child(hub)
    path_target = AliasBlock(label="different_leaf", registry=graph)
    identifier_target = IdentifierOnlyBlock(label="logical.alias", registry=graph)
    scope.add_child(identifier_target)
    assert _resolve_ref(hub, "logical.alias", kind=Block) is path_target
    scoped = IdentifierOnlyBlock(label="scope.short", registry=graph)
    assert _resolve_ref(hub, "short", kind=Block) is scoped
    unscoped = IdentifierOnlyBlock(label="short", registry=graph)
    assert _resolve_ref(hub, "short", kind=Block) is unscoped
    graph.remove(unscoped.uid)
    assert _resolve_ref(hub, "short", kind=Block) is scoped


def test_nearest_path_wins_and_equal_distance_keeps_insertion_order() -> None:
    graph = StoryGraph()
    root = Scene(label="root", registry=graph)
    local = Scene(label="local", registry=graph)
    remote = Scene(label="remote", registry=graph)
    root.add_child(local)
    root.add_child(remote)
    hub = SandboxLocation(label="hub", registry=graph)
    local.add_child(hub)
    far = Block(label="event", registry=graph)
    remote.add_child(far)
    first = Block(label="event", registry=graph)
    second = Block(label="event", registry=graph)
    local.add_child(first)
    local.add_child(second)
    assert graph.path_dist(hub, first) < graph.path_dist(hub, far)
    assert graph.path_dist(hub, first) == graph.path_dist(hub, second)
    assert _resolve_ref(hub, "*.event", kind=Block) is first
    graph.remove(first.uid)
    assert _resolve_ref(hub, "*.event", kind=Block) is second


def test_lookup_sees_add_reparent_relabel_and_removed_targets() -> None:
    graph = StoryGraph()
    hub = SandboxLocation(label="hub", registry=graph)
    first = Scene(label="first", registry=graph)
    second = Scene(label="second", registry=graph)
    assert _resolve_ref(hub, "first.target", kind=Block) is None
    target = Block(label="target", registry=graph)
    first.add_child(target)
    assert _resolve_ref(hub, "first.target", kind=Block) is target
    first.remove_child(target)
    second.add_child(target)
    assert _resolve_ref(hub, "first.target", kind=Block) is None
    assert _resolve_ref(hub, "second.target", kind=Block) is target
    target.label = "renamed"
    assert _resolve_ref(hub, "second.target", kind=Block) is None
    assert _resolve_ref(hub, "second.renamed", kind=Block) is target
    graph.remove(target.uid)
    assert _resolve_ref(hub, "second.renamed", kind=Block) is None
    assert _resolve_ref(SandboxLocation(), "missing", kind=Block) is None


def test_kind_gate_is_python_instance_not_delegated_token_kind() -> None:
    graph = StoryGraph()
    hub = SandboxLocation(label="hub", registry=graph)
    definition = TraversableSuggestion(label="suggestion")
    try:
        token = Token[TraversableSuggestion](token_from=definition.label, label="collision",
                                             registry=graph)
        assert token.has_kind(TraversableNode) and not isinstance(token, TraversableNode)
        assert _resolve_ref(hub, "collision", kind=TraversableNode) is None
        actual = Block(label="collision", registry=graph)
        assert _resolve_ref(hub, "collision", kind=TraversableNode) is actual
        wrong = Block(label="place", registry=graph)
        assert _resolve_ref(hub, "place", kind=SandboxLocation) is None
        place = SandboxLocation(label="place", registry=graph)
        assert _resolve_ref(hub, "place", kind=SandboxLocation) is place
        assert wrong is not place
    finally:
        TraversableSuggestion.clear_instances()


@pytest.mark.parametrize("reference", ["chapter.event_0", "chapter.event_*", "absent"])
def test_path_work_scales_with_eligible_candidates_only(
    reference: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = StoryGraph()
    hub = SandboxLocation(label="hub", registry=graph)
    targets = [Scene(label=f"chapter.event_{i}", registry=graph) for i in range(3)]
    for i in range(200):
        graph.add(Node(label=f"unrelated_{i}"))
    checked = []
    original = GraphItem.has_path

    def eligible_path(member: GraphItem, pattern: str) -> bool:
        assert isinstance(member, TraversableNode), "unrelated member paid for path construction"
        checked.append(member.uid)
        return original(member, pattern)

    monkeypatch.setattr(GraphItem, "has_path", eligible_path)
    result = _resolve_ref(hub, reference, kind=TraversableNode)
    assert checked == [hub.uid, *(target.uid for target in targets)]
    assert result is (None if reference == "absent" else targets[0])
