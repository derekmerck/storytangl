"""Contract tests for ``tangl.vm38.provision.resolver``.

Organized by concept:
- Offer gathering: FindProvisioner, TemplateProvisioner, FallbackProvisioner
- Requirement resolution: single vs ambiguous offers
- Dependency resolution: provider linking
- Frontier resolution: full node satisfaction check
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core38 import BehaviorRegistry, Entity, EntityTemplate, Graph, Registry, RegistryAware, Selector
from tangl.vm38.provision import (
    Dependency,
    FindProvisioner,
    InlineTemplateProvisioner,
    ProvisionPolicy,
    Requirement,
    Resolver,
    FallbackProvisioner,
)
from tangl.vm38.traversable import TraversableNode


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _dependency(graph: Graph, **kwargs) -> Dependency:
    dependency = Dependency(**kwargs)
    graph.add(dependency)
    return dependency


# ============================================================================
# FindProvisioner — search existing entities
# ============================================================================


class TestFindProvisioner:
    def test_finds_matching_entity(self) -> None:
        e = Entity(label="sword")
        prov = FindProvisioner(values=[e])
        req = Requirement.from_identifier("sword")
        offers = list(prov.get_dependency_offers(req))
        assert len(offers) == 1
        assert offers[0].policy == ProvisionPolicy.EXISTING

    def test_no_match_no_offers(self) -> None:
        e = Entity(label="shield")
        prov = FindProvisioner(values=[e])
        req = Requirement.from_identifier("sword")
        offers = list(prov.get_dependency_offers(req))
        assert len(offers) == 0

    def test_callback_returns_entity(self) -> None:
        e = Entity(label="sword")
        prov = FindProvisioner(values=[e])
        req = Requirement.from_identifier("sword")
        offers = list(prov.get_dependency_offers(req))
        result = offers[0].callback()
        assert result is e

    def test_distance_affects_priority(self) -> None:
        e = Entity(label="sword")
        near = FindProvisioner(values=[e], distance=0)
        far = FindProvisioner(values=[e], distance=5)
        req = Requirement.from_identifier("sword")
        near_offer = list(near.get_dependency_offers(req))[0]
        far_offer = list(far.get_dependency_offers(req))[0]
        assert near_offer.sort_key() < far_offer.sort_key()


# ============================================================================
# Resolver — orchestrated resolution
# ============================================================================


class TestResolverOfferGathering:
    def test_gathers_from_entity_groups(self) -> None:
        e = Entity(label="sword")
        resolver = Resolver(entity_groups=[[e]])
        req = Requirement.from_identifier("sword")
        offers = resolver.gather_offers(req)
        assert len(offers) >= 1

    def test_empty_groups_yield_force_fallback_only_when_forced(self) -> None:
        resolver = Resolver(entity_groups=[], template_groups=[])
        req = Requirement.from_identifier("missing")
        offers = resolver.gather_offers(req, force=True)
        assert any(o.policy == ProvisionPolicy.FORCE for o in offers)

        no_force_offers = resolver.gather_offers(req, force=False)
        assert no_force_offers == []

    def test_force_fallback_not_selected_when_non_force_offer_exists(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]], template_groups=[])
        req = Requirement.from_identifier("sword")
        offers = resolver.gather_offers(req, force=True)
        assert len(offers) == 1
        assert all(o.policy != ProvisionPolicy.FORCE for o in offers)

    def test_force_fallback_synthesizes_kind_and_identifier(self) -> None:
        class Person(Entity):
            pass

        resolver = Resolver(entity_groups=[], template_groups=[])
        req = Requirement(has_kind=Person, has_identifier="joe")
        provider = resolver.resolve_requirement(req, force=True)
        assert isinstance(provider, Person)
        assert provider.label == "joe"

    def test_inline_template_provisioner_offers_create(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "castle"})
        req = Requirement(has_identifier="castle", fallback_templ=template)
        offers = list(InlineTemplateProvisioner.get_dependency_offers(req))
        assert len(offers) == 1
        assert offers[0].policy == ProvisionPolicy.CREATE

    def test_distance_prefers_nearest_group(self) -> None:
        near = Entity(label="provider")
        far = Entity(label="provider")
        resolver = Resolver(location_entity_groups=[[near], [far]])
        req = Requirement(has_identifier="provider")
        provider = resolver.resolve_requirement(req)
        assert provider is near

    def test_specificity_prefers_exact_kind_when_distance_equal(self) -> None:
        class SpecialEntity(Entity):
            pass

        special = SpecialEntity(label="special")
        plain = Entity(label="plain")
        resolver = Resolver(location_entity_groups=[[special, plain]])
        req = Requirement(has_kind=Entity)
        offers = resolver.gather_offers(req)
        assert offers
        assert offers[0].candidate is plain


class TestResolverRequirementResolution:
    def test_resolves_existing_entity(self) -> None:
        e = Entity(label="sword")
        resolver = Resolver(entity_groups=[[e]])
        req = Requirement.from_identifier("sword")
        provider = resolver.resolve_requirement(req)
        assert provider is e

    def test_no_match_marks_unsatisfiable(self) -> None:
        resolver = Resolver(entity_groups=[])
        req = Requirement(has_identifier="missing", provision_policy=ProvisionPolicy.EXISTING)
        provider = resolver.resolve_requirement(req)
        # EXISTING-only policy filters out FORCE fallbacks
        assert provider is None
        assert req.unsatisfiable is True
        assert req.resolution_reason == "no_offers"

    def test_force_with_existing_offer_prefers_existing(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]])
        req = Requirement.from_identifier("sword")
        provider = resolver.resolve_requirement(req, force=True)
        assert provider is sword
        assert req.selected_offer_policy == ProvisionPolicy.EXISTING

    def test_from_ctx_requires_provision_context_shape(self) -> None:
        ctx = SimpleNamespace()
        with pytest.raises(TypeError, match="get_location_entity_groups|get_entity_groups"):
            Resolver.from_ctx(ctx)

    def test_invalid_resolve_override_sets_override_reason(self) -> None:
        def bad_override(*, caller, offers, ctx, **kw):
            return ["not-an-offer"]

        local_registry = BehaviorRegistry(label="test_resolve_req_registry")
        local_registry.register(func=bad_override, task="resolve_req")
        ctx = SimpleNamespace(
            get_registries=lambda: [local_registry],
            get_inline_behaviors=lambda: [],
        )
        resolver = Resolver(entity_groups=[])
        req = Requirement(has_identifier="missing", provision_policy=ProvisionPolicy.EXISTING)
        provider = resolver.resolve_requirement(req, _ctx=ctx)
        assert provider is None
        assert req.resolution_reason == "override_invalid"
        assert req.resolution_meta is not None
        assert "error" in req.resolution_meta


class TestResolverDependencyResolution:
    def test_resolve_dependency_links_provider(self) -> None:
        reg = Registry()
        sword = RegistryAware(label="sword")
        reg.add(sword)
        dep = Dependency(requirement=Requirement.from_identifier("sword"))
        reg.add(dep)

        resolver = Resolver(entity_groups=[[sword]])
        success = resolver.resolve_dependency(dep)
        assert success is True
        assert dep.satisfied
        assert dep.provider is sword

    def test_resolve_dependency_sets_resolution_metadata(self) -> None:
        g = Graph()
        node = _node(g, label="room")
        sword = _node(g, label="sword")
        dep = _dependency(
            g,
            requirement=Requirement.from_identifier("sword"),
            predecessor_id=node.uid,
        )
        ctx = SimpleNamespace(
            step=3,
            cursor_id=node.uid,
            get_registries=lambda: [],
            get_inline_behaviors=lambda: [],
        )

        resolver = Resolver(entity_groups=[[sword]])
        success = resolver.resolve_dependency(dep, _ctx=ctx)
        assert success is True
        assert dep.requirement.resolved_step == 3
        assert dep.requirement.resolved_cursor_id == node.uid

    def test_force_fallback_bypasses_requirement_validation(self) -> None:
        class Person(RegistryAware):
            pass

        g = Graph()
        node = _node(g, label="room")
        dep = _dependency(
            g,
            requirement=Requirement(
                has_kind=Person,
                has_identifier=b"joe",  # deliberately unsatisfiable by synthesized label
            ),
            predecessor_id=node.uid,
        )

        resolver = Resolver(entity_groups=[], template_groups=[])
        ctx = SimpleNamespace(
            step=11,
            cursor_id=node.uid,
            get_registries=lambda: [],
            get_inline_behaviors=lambda: [],
        )
        success = resolver.resolve_dependency(dep, force=True, _ctx=ctx)
        assert success is True
        assert dep.provider is not None
        assert isinstance(dep.provider, Person)
        assert dep.satisfied
        assert dep.requirement.selected_offer_policy == ProvisionPolicy.FORCE
        assert dep.requirement.resolved_step == 11
        assert dep.requirement.resolved_cursor_id == node.uid


class TestResolverFrontierNode:
    def test_node_with_all_deps_satisfied(self) -> None:
        g = Graph()
        node = _node(g, label="room")
        sword = _node(g, label="sword")

        dep = _dependency(
            g,
            requirement=Requirement.from_identifier("sword"),
            predecessor_id=node.uid,
        )

        resolver = Resolver(entity_groups=[[sword]])
        result = resolver.resolve_frontier_node(node)
        assert result is True
        assert dep.satisfied

    def test_node_with_unresolvable_deps(self) -> None:
        g = Graph()
        node = _node(g, label="room")
        dep = _dependency(g, 
            requirement=Requirement(
                has_identifier="missing",
                provision_policy=ProvisionPolicy.EXISTING,
            ), predecessor_id=node.uid,
        )

        resolver = Resolver(entity_groups=[])
        result = resolver.resolve_frontier_node(node)
        assert result is False

    def test_container_without_progress_is_not_viable(self) -> None:
        g = Graph()
        container = _node(g, label="scene")
        source = _node(g, label="entry")
        sink = _node(g, label="exit")
        container.add_child(source)
        container.add_child(sink)
        container.source_id = source.uid
        container.sink_id = sink.uid
        resolver = Resolver(entity_groups=[])
        assert resolver.resolve_frontier_node(container) is False
