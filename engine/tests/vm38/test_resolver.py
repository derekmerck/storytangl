"""Contract tests for ``tangl.vm38.provision.resolver``.

Organized by concept:
- Offer gathering: FindProvisioner, TemplateProvisioner, FallbackProvisioner
- Requirement resolution: single vs ambiguous offers
- Dependency resolution: provider linking
- Frontier resolution: full node satisfaction check
"""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core38 import Entity, EntityTemplate, Graph, Registry, RegistryAware, Selector
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

    def test_force_with_existing_offer_prefers_existing(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]])
        req = Requirement.from_identifier("sword")
        provider = resolver.resolve_requirement(req, force=True)
        assert provider is sword
        assert req.selected_offer_policy == ProvisionPolicy.EXISTING


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
        success = resolver.resolve_dependency(dep, force=True)
        assert success is True
        assert dep.provider is not None
        assert isinstance(dep.provider, Person)
        assert dep.satisfied
        assert dep.requirement.selected_offer_policy == ProvisionPolicy.FORCE


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
