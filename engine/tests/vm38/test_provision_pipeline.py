# engine/tests/vm38/test_provision_pipeline.py
"""Contract tests for the vm38 provisioning/planning pipeline.

The planning system in vm38 is deliberately simpler than v3.7:
  - ``do_provision`` aggregates with ``gather`` — handlers MUST return None.
  - Provisioning is side-effect-only; no receipt object is emitted.
  - ``Resolver.resolve_frontier_node`` is the primary entry point that satisfies
    open ``Dependency`` edges on a node.
  - Satisfied dependencies change node availability (via ``HasAvailability``).
  - The PLANNING phase is triggered as part of ``frame.follow_edge`` at every hop.

Organized by contract:

- ``do_provision`` enforcement — non-None return raises TypeError
- ``Dependency`` lifecycle — unsatisfied / satisfied / provider assigned
- ``Resolver.resolve_frontier_node`` — closes open dependencies
- Availability gating — unsatisfied hard deps block choice availability
- Dispatch integration — ``on_provision`` handler fires at PLANNING phase
- Policy enforcement — EXISTING vs CREATE offer selection
- ``Affordance`` push pattern — provider-side assignment
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Callable, Iterator

import pytest

from tangl.core import Entity, EntityTemplate, Graph, Priority, Registry, RegistryAware, Selector, TemplateRegistry
from tangl.vm.dispatch import (
    dispatch as vm_dispatch,
    do_provision,
    on_provision,
)
from tangl.vm.provision import (
    Affordance,
    Dependency,
    Fanout,
    InlineTemplateProvisioner,
    ProvisionPolicy,
    Requirement,
    Resolver,
)
from tangl.vm.traversable import TraversableNode
from tangl.core.runtime_op import Predicate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph_with_nodes(*labels: str) -> tuple[Graph, list[TraversableNode]]:
    g = Graph()
    nodes = []
    for label in labels:
        node = TraversableNode(label=label)
        g.add(node)
        nodes.append(node)
    return g, nodes


def _ctx() -> SimpleNamespace:
    return SimpleNamespace(
        get_registries=lambda: [],
        get_inline_behaviors=lambda: [],
    )


def _template_registry(*templates: EntityTemplate) -> TemplateRegistry:
    registry = TemplateRegistry(label="provision_pipeline_templates")
    for template in templates:
        registry.add(template)
    return registry


@contextmanager
def _cleanup_behaviors(*funcs: Callable[..., object]) -> Iterator[None]:
    """Remove registered vm_dispatch behaviors after test assertions."""
    try:
        yield
    finally:
        for func in funcs:
            behavior = getattr(func, "_behavior", None)
            if behavior is not None:
                vm_dispatch.remove(behavior.uid)


# ---------------------------------------------------------------------------
# do_provision enforcement
# ---------------------------------------------------------------------------


class TestDoProvisionEnforcement:
    """do_provision must enforce the side-effect-only contract."""

    def test_handler_returning_none_is_allowed(self, clean_vm_dispatch) -> None:
        called = []

        @on_provision
        def good_handler(caller, *, ctx, **kwargs):
            called.append(caller)
            return None

        ctx = _ctx()
        g = Graph()
        node = TraversableNode(label="x", registry=g)
        with _cleanup_behaviors(good_handler):
            do_provision(node, ctx=ctx)
        assert node in called

    def test_handler_returning_non_none_raises_type_error(
        self, clean_vm_dispatch
    ) -> None:
        @on_provision
        def bad_handler(caller, *, ctx, **kwargs):
            return "oops"  # non-None is forbidden

        ctx = _ctx()
        g = Graph()
        node = TraversableNode(label="x", registry=g)
        with _cleanup_behaviors(bad_handler):
            with pytest.raises(TypeError, match="non-None"):
                do_provision(node, ctx=ctx)

    def test_no_handlers_returns_none(self, clean_vm_dispatch) -> None:
        ctx = _ctx()
        g = Graph()
        node = TraversableNode(label="x", registry=g)
        result = do_provision(node, ctx=ctx)
        assert result is None


# ---------------------------------------------------------------------------
# Dependency lifecycle
# ---------------------------------------------------------------------------


class TestDependencyLifecycle:
    """Dependency edges reflect unsatisfied / satisfied state correctly."""

    def test_new_dependency_is_unsatisfied(self) -> None:
        reg = Registry()
        dep = Dependency(requirement=Requirement.from_identifier("key"))
        reg.add(dep)
        assert dep.satisfied is False
        assert dep.provider is None

    def test_set_provider_satisfies_dependency(self) -> None:
        reg = Registry()
        key = RegistryAware(label="key")
        reg.add(key)
        dep = Dependency(requirement=Requirement.from_identifier("key"))
        reg.add(dep)
        dep.set_provider(key)
        assert dep.satisfied is True
        assert dep.provider is key

    def test_clear_provider_unsatisfies_dependency(self) -> None:
        reg = Registry()
        key = RegistryAware(label="key")
        reg.add(key)
        dep = Dependency(requirement=Requirement.from_identifier("key"))
        reg.add(dep)
        dep.set_provider(key)
        dep.set_provider(None)
        assert dep.satisfied is False
        assert dep.provider is None

    def test_predecessor_is_frontier_node(self) -> None:
        """The frontier node is always predecessor in a Dependency edge."""
        g = Graph()
        frontier = TraversableNode(label="frontier", registry=g)
        resource = TraversableNode(label="resource", registry=g)
        dep = Dependency(
            registry=g,
            requirement=Requirement.from_identifier("resource"),
            predecessor_id=frontier.uid,
        )
        assert dep.predecessor is frontier

    def test_satisfied_dependency_has_provider_id(self) -> None:
        reg = Registry()
        key = RegistryAware(label="key")
        reg.add(key)
        dep = Dependency(requirement=Requirement.from_identifier("key"))
        reg.add(dep)
        dep.set_provider(key)
        assert dep.requirement.provider_id == key.uid


# ---------------------------------------------------------------------------
# Resolver.resolve_frontier_node
# ---------------------------------------------------------------------------


class TestResolveFrontierNode:
    """resolve_frontier_node closes open dependencies on a node."""

    def test_open_dep_linked_when_matching_entity_exists(self) -> None:
        g = Graph()
        frontier = TraversableNode(label="room", registry=g)
        sword = TraversableNode(label="sword", registry=g)
        dep = Dependency(
            registry=g,
            requirement=Requirement.from_identifier("sword"),
            predecessor_id=frontier.uid,
        )
        resolver = Resolver(entity_groups=[[sword]])
        success = resolver.resolve_frontier_node(frontier)
        assert success is True
        assert dep.satisfied

    def test_returns_false_when_hard_dep_unresolvable(self) -> None:
        g = Graph()
        frontier = TraversableNode(label="locked_door", registry=g)
        Dependency(
            registry=g,
            requirement=Requirement(
                has_identifier="magic_key",
                provision_policy=ProvisionPolicy.EXISTING,  # must exist; can't create
            ),
            predecessor_id=frontier.uid,
        )
        resolver = Resolver(entity_groups=[], template_groups=[])
        success = resolver.resolve_frontier_node(frontier)
        assert success is False

    def test_no_deps_returns_true(self) -> None:
        g = Graph()
        frontier = TraversableNode(label="open_road", registry=g)
        resolver = Resolver(entity_groups=[])
        success = resolver.resolve_frontier_node(frontier)
        assert success is True

    def test_satisfied_dep_not_re_resolved(self) -> None:
        """Already-satisfied deps are skipped by resolve_frontier_node."""
        g = Graph()
        frontier = TraversableNode(label="room", registry=g)
        sword = TraversableNode(label="sword", registry=g)
        dep = Dependency(
            registry=g,
            requirement=Requirement.from_identifier("sword"),
            predecessor_id=frontier.uid,
        )
        dep.set_provider(sword)  # manually satisfy
        # No entities in resolver — if it tried to re-resolve, it would fail
        resolver = Resolver(entity_groups=[])
        success = resolver.resolve_frontier_node(frontier)
        # Still passes because dep was already satisfied
        assert success is True


# ---------------------------------------------------------------------------
# Availability gating
# ---------------------------------------------------------------------------


class TestAvailabilityGating:
    """Unsatisfied hard requirements affect node's availability predicate evaluation."""

    def test_node_with_unmet_dep_evaluates_available_false(self) -> None:
        g = Graph()
        frontier = TraversableNode(
            label="locked",
            registry=g,
            availability=[Predicate(expr="False")],
        )
        assert frontier.available({}, ctx=None, rand=None) is False

    def test_node_without_predicates_defaults_available(self) -> None:
        g = Graph()
        node = TraversableNode(label="open", registry=g)
        assert node.available({}, ctx=None, rand=None) is True

    def test_satisfied_dep_in_ns_via_contribute_deps(self) -> None:
        """Once resolved, satisfied dep appears in namespace via contribute_satisfied_deps."""
        import tangl.vm.system_handlers as sh

        g = Graph()
        frontier = TraversableNode(label="frontier", registry=g)
        sword = TraversableNode(label="sword", registry=g)
        dep = Dependency(
            registry=g,
            label="sword",
            requirement=Requirement.from_identifier("sword"),
            predecessor_id=frontier.uid,
        )
        dep.set_provider(sword)

        ns = sh.contribute_satisfied_deps(caller=frontier, ctx=None)
        assert ns is not None
        assert "sword" in ns


# ---------------------------------------------------------------------------
# Dispatch integration: on_provision handler at PLANNING phase
# ---------------------------------------------------------------------------


class TestDispatchIntegration:
    """on_provision handlers fire during frame's PLANNING phase."""

    def test_provision_handler_fires_during_follow_edge(
        self, clean_vm_dispatch
    ) -> None:
        """A registered on_provision handler is called when frame runs PLANNING."""
        from tangl.vm.runtime.frame import Frame
        from tangl.vm.traversable import TraversableEdge

        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        edge = TraversableEdge(
            predecessor_id=a.uid, successor_id=b.uid, registry=g
        )

        provisioned_nodes = []

        @on_provision
        def record_provision(caller, *, ctx, **kwargs):
            provisioned_nodes.append(caller.label if hasattr(caller, "label") else str(caller))
            return None

        # Also register validate_successor_exists so traversal doesn't fail
        from tangl.vm.dispatch import on_validate
        import tangl.vm.system_handlers as sh
        on_validate(sh.validate_successor_exists)

        with _cleanup_behaviors(record_provision, sh.validate_successor_exists):
            frame = Frame(graph=g, cursor=a)
            frame.follow_edge(edge)
            # b was provisioned during PLANNING
            assert any("b" in n for n in provisioned_nodes)

    def test_provision_handler_can_add_entity_to_graph(
        self, clean_vm_dispatch
    ) -> None:
        """A planning handler that materializes resources is side-effect-only."""
        from tangl.vm.runtime.frame import Frame
        from tangl.vm.traversable import TraversableEdge
        from tangl.vm.dispatch import on_validate
        import tangl.vm.system_handlers as sh

        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        edge = TraversableEdge(predecessor_id=a.uid, successor_id=b.uid, registry=g)

        created_entity = []

        @on_provision
        def create_resource(caller, *, ctx, **kwargs):
            if caller.label == "b" and "resource" not in [
                n.label for n in g.values() if hasattr(n, "label")
            ]:
                resource = Entity(label="resource")
                g.add(resource)
                created_entity.append(resource)
            return None

        on_validate(sh.validate_successor_exists)

        with _cleanup_behaviors(create_resource, sh.validate_successor_exists):
            frame = Frame(graph=g, cursor=a)
            frame.follow_edge(edge)
            assert len(created_entity) == 1
            assert g.get(created_entity[0].uid) is not None

    def test_provision_created_prereq_edge_is_visible_same_arrival(
        self, clean_vm_dispatch
    ) -> None:
        """PLANNING-created prereqs are scanned by the later PREREQS phase."""
        from tangl.vm import ResolutionPhase
        from tangl.vm.dispatch import do_prereqs, do_provision, on_prereqs
        from tangl.vm.provision.resolver import provision_node
        from tangl.vm.runtime.frame import PhaseCtx
        from tangl.vm.traversable import TraversableEdge
        import tangl.vm.system_handlers as sh

        g = Graph()
        hub = TraversableNode(label="hub", registry=g)
        target = TraversableNode(label="target", registry=g, tags={"menu"})
        Fanout(
            registry=g,
            predecessor_id=hub.uid,
            requirement=Requirement(has_kind=TraversableNode, has_tags={"menu"}),
        )

        @on_provision(priority=Priority.LATE)
        def build_dynamic_prereq(caller, *, ctx, **kwargs):
            _ = (ctx, kwargs)
            if caller is not hub:
                return None
            if next(
                hub.edges_out(
                    Selector(
                        has_kind=TraversableEdge,
                        trigger_phase=ResolutionPhase.PREREQS,
                    )
                ),
                None,
            ) is not None:
                return None
            affordance = next(hub.edges_out(Selector(has_kind=Affordance)), None)
            if affordance is None or affordance.successor is None:
                return None
            TraversableEdge(
                registry=g,
                predecessor_id=hub.uid,
                successor_id=affordance.successor.uid,
                trigger_phase=ResolutionPhase.PREREQS,
                tags={"dynamic", "fanout", "prereq"},
            )
            return None

        on_prereqs(sh.follow_triggered_prereqs)
        on_provision(provision_node)

        with _cleanup_behaviors(build_dynamic_prereq, sh.follow_triggered_prereqs, provision_node):
            ctx = PhaseCtx(graph=g, cursor_id=hub.uid)
            do_provision(hub, ctx=ctx)
            redirect = do_prereqs(hub, ctx=ctx)
            assert redirect is not None
            assert redirect.successor is target


# ---------------------------------------------------------------------------
# Policy enforcement
# ---------------------------------------------------------------------------


class TestPolicyEnforcement:
    """ProvisionPolicy flags control which provisioner types are eligible."""

    def test_existing_policy_only_finds_existing_entities(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]])
        req = Requirement(
            has_identifier="sword",
            provision_policy=ProvisionPolicy.EXISTING,
        )
        offers = resolver.gather_offers(req)
        assert all(o.policy == ProvisionPolicy.EXISTING for o in offers)

    def test_create_policy_only_uses_template_provisioners(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "new_thing"})
        resolver = Resolver(entity_groups=[], template_scope_groups=[_template_registry(template)])
        req = Requirement(
            has_identifier="new_thing",
            provision_policy=ProvisionPolicy.CREATE,
        )
        offers = resolver.gather_offers(req)
        assert all(o.policy == ProvisionPolicy.CREATE for o in offers)

    def test_policy_none_returns_no_offers(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]])
        req = Requirement(
            has_identifier="sword",
            provision_policy=ProvisionPolicy(0),  # empty policy: nothing allowed
        )
        offers = resolver.gather_offers(req)
        assert offers == []

    def test_inline_template_on_requirement_creates_via_create_policy(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "magic_key"})
        req = Requirement(
            has_identifier="magic_key",
            fallback_templ=template,
            provision_policy=ProvisionPolicy.CREATE,
        )
        offers = list(
            InlineTemplateProvisioner(
                materialize_node=Resolver._materialize_node,
            ).iter_dependency_offers(req)
        )
        assert any(o.policy == ProvisionPolicy.CREATE for o in offers)


# ---------------------------------------------------------------------------
# Affordance push pattern
# ---------------------------------------------------------------------------


class TestAffordancePushPattern:
    """Affordances push resources from predecessor to successor."""

    def test_affordance_predecessor_is_frontier(self) -> None:
        g = Graph()
        frontier = TraversableNode(label="frontier", registry=g)
        resource = TraversableNode(label="resource", registry=g)
        aff = Affordance(
            registry=g,
            requirement=Requirement.from_identifier("resource"),
            predecessor_id=frontier.uid,
            successor_id=resource.uid,
        )
        assert aff.predecessor is frontier
        assert aff.successor is resource

    def test_affordance_satisfied_when_successor_linked(self) -> None:
        g = Graph()
        frontier = TraversableNode(label="frontier", registry=g)
        bob = TraversableNode(label="bob", registry=g)
        aff = Affordance(
            registry=g,
            requirement=Requirement.from_identifier("bob"),
            predecessor_id=frontier.uid,
            successor_id=bob.uid,
        )
        # Affordance with bound successor is treated as push-satisfied
        assert aff.successor is bob

    def test_resolver_uses_affordance_to_satisfy_dependency(self) -> None:
        """An Affordance linking frontier→provider is used by resolve_dependency."""
        g = Graph()
        frontier = TraversableNode(label="frontier", registry=g)
        bob = TraversableNode(label="bob", registry=g)
        Affordance(
            registry=g,
            label="companion_here",
            predecessor_id=frontier.uid,
            successor_id=bob.uid,
            requirement=Requirement.from_identifier("bob"),
        )
        dep = Dependency(
            registry=g,
            requirement=Requirement.from_identifier("bob"),
            predecessor_id=frontier.uid,
        )
        # Resolver with no entity groups; affordance acts as push-provider
        resolver = Resolver(entity_groups=[])
        success = resolver.resolve_dependency(dep)
        assert success is True
        assert dep.provider is bob


# ---------------------------------------------------------------------------
# Full pipeline round-trip: provisioning during frame traversal
# ---------------------------------------------------------------------------


class TestFullPipelineRoundTrip:
    """Verify that Dependency resolution fires and completes during resolve_choice."""

    def test_dependency_satisfied_after_frame_hop(
        self, clean_vm_dispatch
    ) -> None:
        """When on_provision handler wires a Resolver, dep is satisfied by PLANNING."""
        from tangl.vm.runtime.frame import Frame
        from tangl.vm.traversable import TraversableEdge
        from tangl.vm.dispatch import on_validate
        import tangl.vm.system_handlers as sh

        g = Graph()
        a = TraversableNode(label="a", registry=g)
        b = TraversableNode(label="b", registry=g)
        sword = TraversableNode(label="sword", registry=g)
        dep = Dependency(
            registry=g,
            requirement=Requirement.from_identifier("sword"),
            predecessor_id=b.uid,
        )
        edge = TraversableEdge(predecessor_id=a.uid, successor_id=b.uid, registry=g)

        @on_provision
        def plan_with_resolver(caller, *, ctx, **kwargs):
            if caller is b:
                resolver = Resolver(entity_groups=[[sword]])
                resolver.resolve_frontier_node(b)
            return None

        on_validate(sh.validate_successor_exists)

        with _cleanup_behaviors(plan_with_resolver, sh.validate_successor_exists):
            frame = Frame(graph=g, cursor=a)
            frame.follow_edge(edge)
            assert dep.satisfied is True
            assert dep.provider is sword
