"""Contract tests for ``tangl.vm.provision.requirement``.

Organized by concept:
- Requirement: satisfaction, matching, policy
- HasRequirement: provider linking
- Dependency: pull-resource edge, provider syncs successor
- Affordance: push-resource edge, provider syncs successor
- Fanout: gather edge, provider ids sync a provider set
"""

from __future__ import annotations

import pytest

from tangl.core import BehaviorRegistry, Entity, Graph, Node, Registry, RegistryAware, Selector
from tangl.vm.provision import (
    Affordance,
    Dependency,
    Fanout,
    HasRequirement,
    ProvisionPolicy,
    Requirement,
)
from tangl.vm.runtime.frame import PhaseCtx


class Person(Entity):
    """An entity kind with a field other kinds lack."""

    age: int = 0


# ============================================================================
# Requirement
# ============================================================================


class TestRequirementSatisfaction:
    def test_unsatisfied_by_default(self) -> None:
        req = Requirement(has_identifier="foo")
        assert not req.satisfied

    def test_satisfied_when_provider_set(self) -> None:
        req = Requirement(has_identifier="foo")
        from uuid import uuid4
        req.provider_id = uuid4()
        assert req.satisfied

    def test_soft_requirement_satisfied_without_provider(self) -> None:
        req = Requirement(hard_requirement=False)
        assert req.satisfied

    def test_satisfied_by_matching_entity(self) -> None:
        e = Entity(label="foo")
        req = Requirement.from_identifier("foo")
        assert req.satisfied_by(e)

    def test_not_satisfied_by_non_matching(self) -> None:
        e = Entity(label="bar")
        req = Requirement.from_identifier("foo")
        assert not req.satisfied_by(e)

    def test_predicate_only_sees_candidates_of_its_kind_and_identifier(self) -> None:
        # The predicate reads `age`, which only a Person has. Checked against a
        # mixed pool it must answer, not raise, for every other candidate.
        req = Requirement(has_kind=Person, has_identifier="joe", predicate=lambda p: p.age >= 18)
        pool = [
            Entity(label="lamp"),
            Entity(label="joe"),
            Person(label="ann", age=30),
            Person(label="joe", age=12),
            Person(label="joe", age=20),
        ]
        assert [e for e in pool if req.satisfied_by(e)] == [pool[4]]


class TestRequirementPolicy:
    def test_default_policy_is_any(self) -> None:
        req = Requirement(has_identifier="foo")
        assert req.provision_policy == ProvisionPolicy.ANY

    def test_custom_policy(self) -> None:
        req = Requirement(
            has_identifier="foo",
            provision_policy=ProvisionPolicy.EXISTING,
        )
        assert req.provision_policy == ProvisionPolicy.EXISTING

    def test_authored_path_defaults(self) -> None:
        req = Requirement(has_identifier="foo")
        assert req.authored_path is None
        assert req.is_qualified is False

    def test_authored_path_metadata_round_trip(self) -> None:
        req = Requirement(
            has_identifier="scene2.block",
            authored_path="block",
            is_qualified=False,
        )
        assert req.authored_path == "block"
        assert req.is_qualified is False


# ============================================================================
# HasRequirement
# ============================================================================


class TestHasRequirement:
    def test_provider_set_and_get(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        provider = RegistryAware(label="foo")
        reg.add(provider)

        carrier.provider = provider
        assert carrier.satisfied
        assert carrier.provider is provider

    def test_provider_mismatch_raises(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        wrong = RegistryAware(label="bar")
        reg.add(wrong)

        with pytest.raises(ValueError, match="not satisfied"):
            carrier.provider = wrong

    def test_provider_sets_resolution_metadata_from_ctx(self) -> None:
        reg = Graph()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        provider = RegistryAware(label="foo")
        reg.add(provider)
        ctx = PhaseCtx(graph=reg, cursor_id=provider.uid, step=7)

        carrier.set_provider(provider, _ctx=ctx)
        assert carrier.requirement.resolved_step == 7
        assert carrier.requirement.resolved_cursor_id == provider.uid

    def test_resolution_reason_and_meta_delegate_from_requirement(self) -> None:
        reg = Registry()
        carrier = HasRequirement(requirement=Requirement(has_identifier="foo"))
        reg.add(carrier)
        carrier.requirement.resolution_reason = "no_offers"
        carrier.requirement.resolution_meta = {"alternatives": []}
        assert carrier.resolution_reason == "no_offers"
        assert carrier.resolution_meta == {"alternatives": []}


# ============================================================================
# Dependency / Affordance — shared provider binding
# ============================================================================


@pytest.mark.parametrize("edge_kind", [Dependency, Affordance])
class TestProviderEdgeContract:
    def test_binding_validation_clearing_and_graph_hooks(self, edge_kind) -> None:
        graph = Graph()
        origin = Node(label="origin", registry=graph)
        provider = Node(label="provider", tags={"suitable"}, registry=graph)
        other = Node(label="other", tags={"suitable"}, registry=graph)
        wrong = Node(label="wrong", registry=graph)
        edge = edge_kind(predecessor_id=origin.uid, requirement=Requirement(has_tags={"suitable"}),
                         registry=graph)
        events = []
        hooks = BehaviorRegistry()
        hooks.register(task="link", func=lambda *, node, **_: events.append(("link", node.uid)))
        hooks.register(task="unlink", func=lambda *, node, **_: events.append(("unlink", node.uid)))
        ctx = PhaseCtx(graph=graph, cursor_id=origin.uid, step=7, local_authorities=[hooks])

        assert not edge.satisfied
        edge.set_provider(provider, _ctx=ctx)
        assert edge.provider is edge.successor is provider
        assert edge.requirement.resolved_step == 7
        assert edge.requirement.resolved_cursor_id == origin.uid
        assert list(graph.find_edges_to(provider)) == [edge]
        for setter in (edge.set_provider, edge.set_successor):
            with pytest.raises(ValueError, match="not satisfied"):
                setter(wrong, _ctx=ctx)
        assert edge.provider is edge.successor is provider
        assert edge.requirement.resolved_step == 7
        assert edge.requirement.resolved_cursor_id == origin.uid
        assert list(graph.find_edges_to(provider)) == [edge]

        edge.set_successor(None, _ctx=ctx)
        assert edge.provider is edge.successor is None and not edge.satisfied
        assert edge.requirement.resolved_step is edge.requirement.resolved_cursor_id is None
        assert list(graph.find_edges_to(provider)) == []
        edge.set_successor(other, _ctx=ctx)
        assert edge.provider is edge.successor is other
        assert edge.requirement.resolved_step == 7
        assert edge.requirement.resolved_cursor_id == origin.uid
        assert list(graph.find_edges_to(other)) == [edge]
        edge.set_provider(None, _ctx=ctx)
        assert edge.provider is edge.successor is None
        assert edge.requirement.resolved_step is edge.requirement.resolved_cursor_id is None
        assert list(graph.find_edges_to(other)) == []
        assert events == [("link", provider.uid), ("unlink", provider.uid),
                          ("link", other.uid), ("unlink", other.uid)]

        edge.successor = provider
        assert edge.provider is edge.successor is provider
        edge.provider = None
        assert edge.provider is edge.successor is None
        edge.provider = other
        assert edge.provider is edge.successor is other
        edge.successor = None
        assert edge.provider is edge.successor is None

    def test_successor_clear_calls_overridden_provider_policy(self, edge_kind) -> None:
        calls = []

        class CustomEdge(edge_kind):
            def set_provider(self, value, _ctx=None):
                calls.append((value, _ctx))
                super().set_provider(value, _ctx=_ctx)

        graph = Graph()
        provider = Node(label="provider", registry=graph)
        edge = CustomEdge(requirement=Requirement(has_identifier="provider"), registry=graph)
        ctx = PhaseCtx(graph=graph, cursor_id=provider.uid, step=3)
        edge.set_successor(provider, _ctx=ctx)
        edge.set_successor(None, _ctx=ctx)
        assert calls == [(provider, ctx), (None, ctx)]


class TestAffordance:
    def test_set_predecessor_does_not_bind_provider(self) -> None:
        reg = Registry()
        aff = Affordance(requirement=Requirement(has_identifier="foo"))
        reg.add(aff)
        frontier = RegistryAware(label="frontier")
        reg.add(frontier)

        aff.set_predecessor(frontier)
        assert aff.predecessor is frontier
        assert aff.provider is None
        assert not aff.satisfied


# ============================================================================
# Fanout — gather resource set
# ============================================================================


class TestFanout:
    def test_set_providers_tracks_multiple_matches(self) -> None:
        graph = Graph()
        hub = RegistryAware(label="hub", registry=graph)
        alpha = RegistryAware(label="alpha", registry=graph, tags={"menu"})
        beta = RegistryAware(label="beta", registry=graph, tags={"menu"})
        fanout = Fanout(
            registry=graph,
            predecessor_id=hub.uid,
            requirement=Requirement(has_tags={"menu"}),
        )

        fanout.set_providers([alpha, beta])

        assert fanout.provider_ids == [alpha.uid, beta.uid]
        assert fanout.providers == [alpha, beta]

    def test_clear_providers_resets_provider_ids(self) -> None:
        graph = Graph()
        hub = RegistryAware(label="hub", registry=graph)
        alpha = RegistryAware(label="alpha", registry=graph, tags={"menu"})
        fanout = Fanout(
            registry=graph,
            predecessor_id=hub.uid,
            requirement=Requirement(has_tags={"menu"}),
        )
        fanout.set_providers([alpha])

        fanout.clear_providers()

        assert fanout.provider_ids == []
        assert fanout.providers == []

    def test_set_providers_rejects_non_matching_provider(self) -> None:
        graph = Graph()
        hub = RegistryAware(label="hub", registry=graph)
        wrong = RegistryAware(label="wrong", registry=graph, tags={"other"})
        fanout = Fanout(
            registry=graph,
            predecessor_id=hub.uid,
            requirement=Requirement(has_tags={"menu"}),
        )

        with pytest.raises(ValueError, match="not satisfied"):
            fanout.set_providers([wrong])

    def test_set_providers_stamps_resolution_metadata_from_ctx(self) -> None:
        graph = Graph()
        hub = RegistryAware(label="hub", registry=graph, tags={"hub"})
        provider = RegistryAware(label="alpha", registry=graph, tags={"menu"})
        fanout = Fanout(
            registry=graph,
            predecessor_id=hub.uid,
            requirement=Requirement(has_tags={"menu"}),
        )
        ctx = PhaseCtx(graph=graph, cursor_id=hub.uid, step=5)

        fanout.set_providers([provider], _ctx=ctx)

        assert fanout.requirement.resolved_step == 5
        assert fanout.requirement.resolved_cursor_id == hub.uid
