"""Contract tests for ``tangl.vm38.provision.resolver``.

Organized by concept:
- Offer gathering: FindProvisioner, TemplateProvisioner, FallbackProvisioner
- Requirement resolution: single vs ambiguous offers
- Dependency resolution: provider linking
- Frontier resolution: full node satisfaction check
"""

from __future__ import annotations

from random import Random
from types import SimpleNamespace
from uuid import UUID

import pytest

from tangl.core38 import (
    BehaviorRegistry,
    Entity,
    EntityTemplate,
    Graph,
    Priority,
    Registry,
    RegistryAware,
    Selector,
    Singleton,
    TemplateRegistry,
    Token,
    TokenCatalog,
)
from tangl.vm38.provision import (
    Affordance,
    Dependency,
    FindProvisioner,
    InlineTemplateProvisioner,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TemplateProvisioner,
    FallbackProvisioner,
    ProvisionOffer,
)
from tangl.vm38.traversable import TraversableNode


class FinalizableContainer(TraversableNode):
    finalize_calls: int = 0

    def finalize_container_contract(self) -> None:
        self.finalize_calls += 1
        children = list(self.children())
        if children:
            if self.source_id is None:
                self.source_id = children[0].uid
            if self.sink_id is None:
                self.sink_id = children[-1].uid


def _node(graph: Graph, **kwargs) -> TraversableNode:
    node = TraversableNode(**kwargs)
    graph.add(node)
    return node


def _dependency(graph: Graph, **kwargs) -> Dependency:
    dependency = Dependency(**kwargs)
    graph.add(dependency)
    return dependency


def _ctx_with_seed(seed: int) -> SimpleNamespace:
    rng = Random(seed)
    return SimpleNamespace(
        get_registries=lambda: [],
        get_inline_behaviors=lambda: [],
        get_random=lambda: rng,
    )


def _ctx_with_token_catalogs(*catalogs: TokenCatalog) -> SimpleNamespace:
    registry = BehaviorRegistry(label="token_catalog_registry")

    def _catalogs(*, caller, requirement, ctx, **kw):
        return list(catalogs)
    registry.register(func=_catalogs, task="get_token_catalogs")

    return SimpleNamespace(
        cursor=None,
        get_authorities=lambda: [registry],
        get_registries=lambda: [registry],
        get_inline_behaviors=lambda: [],
    )


def _template_registry(*templates: EntityTemplate) -> TemplateRegistry:
    registry = TemplateRegistry(label="resolver_test_templates")
    for template in templates:
        registry.add(template)
    return registry


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

    def test_dotted_identifier_matches_existing_entity_path(self) -> None:
        graph = Graph()
        scene = TraversableNode(label="scene2", registry=graph)
        entry = TraversableNode(label="entry", registry=graph)
        scene.add_child(entry)

        prov = FindProvisioner(values=[entry])
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="scene2.entry",
        )
        offers = list(prov.get_dependency_offers(req))

        assert len(offers) == 1
        assert offers[0].callback() is entry


# ============================================================================
# Resolver — orchestrated resolution
# ============================================================================


class TestResolverOfferGathering:
    def test_materialize_node_role_policy_uses_hook_only_for_leaf(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "crafted"})
        hook_calls: list[str] = []

        def hook(templ: EntityTemplate, _ctx=None):
            hook_calls.append(templ.get_label())
            return templ.materialize()

        leaf = Resolver._materialize_node(
            template,
            role="provision_leaf",
            story_materialize=hook,
        )
        init = Resolver._materialize_node(
            template,
            role="init",
            story_materialize=hook,
        )
        intermediate = Resolver._materialize_node(
            template,
            role="provision_intermediate",
            story_materialize=hook,
        )

        assert hook_calls == [template.get_label()]
        assert leaf.templ_hash == template.content_hash().hex()
        assert init.templ_hash == template.content_hash().hex()
        assert intermediate.templ_hash == template.content_hash().hex()

    def test_materialize_node_uid_falls_back_without_rng_context(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "crafted"})
        provider = Resolver._materialize_node(
            template,
            _ctx=SimpleNamespace(),
            role="init",
        )
        assert isinstance(provider.uid, UUID)

    def test_template_create_offer_uses_ctx_rng_for_uid(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "crafted"})
        resolver = Resolver(location_entity_groups=[], template_scope_groups=[_template_registry(template)])
        req = Requirement(has_identifier="crafted", provision_policy=ProvisionPolicy.CREATE)

        seed = 1729
        provider = resolver.resolve_requirement(req, _ctx=_ctx_with_seed(seed))

        assert provider is not None
        assert provider.uid == UUID(int=Random(seed).getrandbits(128), version=4)
        assert req.selected_offer_policy == ProvisionPolicy.CREATE

    def test_inline_template_offer_uses_ctx_rng_for_uid(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "inline"})
        req = Requirement(
            has_identifier="inline",
            fallback_templ=template,
            provision_policy=ProvisionPolicy.CREATE,
        )
        offer = list(
            InlineTemplateProvisioner(
                materialize_node=Resolver._materialize_node,
            ).iter_dependency_offers(req)
        )[0]

        seed = 71
        provider = offer.callback(_ctx=_ctx_with_seed(seed))

        assert provider.uid == UUID(int=Random(seed).getrandbits(128), version=4)

    def test_inline_template_classmethod_shim_raises(self) -> None:
        req = Requirement(
            has_identifier="inline",
            fallback_templ=EntityTemplate(payload={"kind": Entity, "label": "inline"}),
            provision_policy=ProvisionPolicy.CREATE,
        )
        with pytest.raises(NotImplementedError, match="classmethod shim was removed"):
            list(InlineTemplateProvisioner.get_dependency_offers(req))

    def test_template_provisioner_materialize_requires_materialize_node(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "crafted"})
        req = Requirement(
            has_identifier="crafted",
            provision_policy=ProvisionPolicy.CREATE,
        )
        provisioner = TemplateProvisioner(
            registries=[_template_registry(template)],
            request_ctx="",
            graph=Graph(),
            materialize_node=None,
        )
        offer = list(provisioner.get_dependency_offers(req))[0]
        with pytest.raises(RuntimeError, match="requires materialize_node"):
            offer.callback()

    def test_token_catalog_offer_creates_token_provider(self) -> None:
        class GearType(Singleton):
            pass

        GearType(label="torch")
        catalog = TokenCatalog(wst=GearType)
        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        req = Requirement(
            has_kind=GearType,
            has_identifier="torch",
            provision_policy=ProvisionPolicy.CREATE,
        )

        provider = resolver.resolve_requirement(req, _ctx=_ctx_with_token_catalogs(catalog))
        assert isinstance(provider, Token)
        assert provider.token_from == "torch"
        assert req.selected_offer_policy is not None
        assert bool(req.selected_offer_policy & ProvisionPolicy.TOKEN)

    def test_token_offer_uses_requirement_label_for_materialized_token_only(self) -> None:
        class GearType(Singleton):
            pass

        GearType(label="torch")
        catalog = TokenCatalog(wst=GearType)
        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        req = Requirement(
            has_kind=GearType,
            has_identifier="torch",
            label="inventory_torch",
            provision_policy=ProvisionPolicy.CREATE,
        )

        provider = resolver.resolve_requirement(req, _ctx=_ctx_with_token_catalogs(catalog))
        assert isinstance(provider, Token)
        assert provider.token_from == "torch"
        assert provider.label == "inventory_torch"

    def test_token_offer_uses_exact_catalog_for_subclass_instance(self) -> None:
        class ItemType(Singleton):
            pass

        class ArmorType(ItemType):
            pass

        ArmorType(label="chainmail")
        base_catalog = TokenCatalog(wst=ItemType)
        armor_catalog = TokenCatalog(wst=ArmorType)
        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        req = Requirement(
            has_kind=ItemType,
            has_identifier="chainmail",
            provision_policy=ProvisionPolicy.CREATE,
        )

        provider = resolver.resolve_requirement(
            req,
            _ctx=_ctx_with_token_catalogs(base_catalog, armor_catalog),
        )
        assert isinstance(provider, Token)
        assert provider.token_from == "chainmail"
        assert provider.__class__.wrapped_cls is ArmorType

    def test_existing_offer_beats_token_create_offer(self) -> None:
        class GearType(Singleton):
            pass

        GearType(label="torch")
        existing = Token[GearType](token_from="torch", label="existing")
        catalog = TokenCatalog(wst=GearType)
        resolver = Resolver(location_entity_groups=[[existing]], template_scope_groups=[])
        req = Requirement(
            has_kind=GearType,
            has_identifier="torch",
        )

        provider = resolver.resolve_requirement(req, _ctx=_ctx_with_token_catalogs(catalog))
        assert provider is existing
        assert req.selected_offer_policy == ProvisionPolicy.EXISTING

    def test_update_clone_ignores_token_create_offers(self) -> None:
        class PatchType(Singleton):
            pass

        PatchType(label="patched")
        source = Entity(label="source")
        catalog = TokenCatalog(wst=PatchType)
        resolver = Resolver(location_entity_groups=[[source]], template_scope_groups=[])
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.UPDATE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        offers = resolver.gather_offers(req, _ctx=_ctx_with_token_catalogs(catalog))
        assert offers == []

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
        offers = list(
            InlineTemplateProvisioner(
                materialize_node=Resolver._materialize_node,
            ).iter_dependency_offers(req)
        )
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
        assert offers[0].exact_kind_match is True
        assert any(offer.exact_kind_match is False for offer in offers[1:])

    def test_exact_kind_match_sorts_ahead_of_specificity(self) -> None:
        exact = ProvisionOffer(
            policy=ProvisionPolicy.EXISTING,
            callback=lambda: None,
            exact_kind_match=True,
            specificity=0,
        )
        inexact = ProvisionOffer(
            policy=ProvisionPolicy.EXISTING,
            callback=lambda: None,
            exact_kind_match=False,
            specificity=10_000,
        )
        ordered = sorted([inexact, exact], key=lambda offer: offer.sort_key())
        assert ordered[0] is exact

    def test_update_clone_declines_without_two_part_formula(self) -> None:
        source = Entity(label="source")
        template = EntityTemplate(payload={"kind": Entity, "label": "patched"})
        resolver = Resolver(
            location_entity_groups=[[source]],
            template_scope_groups=[_template_registry(template)],
        )
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.UPDATE | ProvisionPolicy.CLONE,
        )
        offers = resolver.gather_offers(req)
        assert offers == []

    def test_update_offer_is_deferred_until_selected(self) -> None:
        source = Entity(label="source")
        template = EntityTemplate(payload={"kind": Entity, "label": "patched"})
        resolver = Resolver(
            location_entity_groups=[[source]],
            template_scope_groups=[_template_registry(template)],
        )
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.UPDATE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        offers = resolver.gather_offers(req)
        assert len(offers) == 1
        assert offers[0].policy == ProvisionPolicy.UPDATE
        assert source.label == "source"

        provider = resolver.resolve_requirement(req)
        assert provider is source
        assert source.label == "patched"
        assert req.selected_offer_policy == ProvisionPolicy.UPDATE

    def test_clone_offer_uses_selected_reference_and_template(self) -> None:
        source = Entity(label="source")
        template = EntityTemplate(payload={"kind": Entity, "label": "patched"})
        resolver = Resolver(
            location_entity_groups=[[source]],
            template_scope_groups=[_template_registry(template)],
        )
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.CLONE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        clone = resolver.resolve_requirement(req)
        assert clone is not None
        assert clone is not source
        assert clone.uid != source.uid
        assert clone.label == "patched"
        assert source.label == "source"
        assert req.selected_offer_policy == ProvisionPolicy.CLONE

    def test_clone_offer_inherits_reference_templ_hash(self) -> None:
        source = Entity(label="source")
        source.templ_hash = "refhash123"
        template = EntityTemplate(payload={"kind": Entity, "label": "patched"})
        resolver = Resolver(
            location_entity_groups=[[source]],
            template_scope_groups=[_template_registry(template)],
        )
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.CLONE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        clone = resolver.resolve_requirement(req)
        assert clone is not None
        assert clone.templ_hash == "refhash123"

    def test_clone_offer_uid_is_deterministic_for_same_seed(self) -> None:
        def _resolve(seed: int) -> tuple[Entity, Entity]:
            source = Entity(label="source")
            template = EntityTemplate(payload={"kind": Entity, "label": "patched"})
            resolver = Resolver(
                location_entity_groups=[[source]],
                template_scope_groups=[_template_registry(template)],
            )
            req = Requirement(
                has_kind=Entity,
                provision_policy=ProvisionPolicy.CLONE,
                reference_selector=Selector(has_identifier="source"),
                update_template_selector=Selector(has_identifier="patched"),
            )
            clone = resolver.resolve_requirement(req, _ctx=_ctx_with_seed(seed))
            assert clone is not None
            return source, clone

        source_a, clone_a = _resolve(seed=2026)
        source_b, clone_b = _resolve(seed=2026)

        assert clone_a.uid == clone_b.uid
        assert clone_a.uid != source_a.uid
        assert clone_a.label == "patched"

    def test_update_clone_prefers_ranked_pair_without_eager_callbacks(self) -> None:
        source_primary = Entity(label="source")
        source_secondary = Entity(label="source")
        template_primary = EntityTemplate(payload={"kind": Entity, "label": "patched"})
        template_secondary = EntityTemplate(payload={"kind": Entity, "label": "patched"})

        invocations: list[str] = []

        find_best = ProvisionOffer(
            origin_id="find.best",
            policy=ProvisionPolicy.EXISTING,
            priority=Priority.EARLY,
            distance_from_caller=0,
            candidate=source_primary,
            callback=lambda *_, **__: (invocations.append("find.best"), source_primary)[1],
        )
        find_worse = ProvisionOffer(
            origin_id="find.worse",
            policy=ProvisionPolicy.EXISTING,
            priority=Priority.LATE,
            distance_from_caller=3,
            candidate=source_secondary,
            callback=lambda *_, **__: (invocations.append("find.worse"), source_secondary)[1],
        )
        create_best = ProvisionOffer(
            origin_id="create.best",
            policy=ProvisionPolicy.CREATE,
            priority=Priority.EARLY,
            distance_from_caller=0,
            candidate=template_primary,
            callback=lambda *_, **__: (invocations.append("create.best"), {"label": "patched_best"})[1],
        )
        create_worse = ProvisionOffer(
            origin_id="create.worse",
            policy=ProvisionPolicy.CREATE,
            priority=Priority.LATE,
            distance_from_caller=3,
            candidate=template_secondary,
            callback=lambda *_, **__: (invocations.append("create.worse"), {"label": "patched_worse"})[1],
        )

        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.UPDATE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        offers = resolver.gather_offers(
            req,
            preferred_offers=[find_worse, create_worse, find_best, create_best],
        )
        assert len(offers) == 1
        assert offers[0].policy == ProvisionPolicy.UPDATE
        assert invocations == []

        provider = resolver.resolve_requirement(
            req,
            preferred_offers=[find_worse, create_worse, find_best, create_best],
        )
        assert provider is source_primary
        assert source_primary.label == "patched_best"
        assert source_secondary.label == "source"
        assert invocations == ["find.best", "create.best"]

    def test_clone_offer_raises_if_reference_rejects_uid_override(self) -> None:
        class NoUidClone(Entity):
            def evolve(self, *, label: str):
                return NoUidClone(uid=self.uid, label=label)

        source = NoUidClone(label="source")
        template = EntityTemplate(payload={"kind": Entity, "label": "patched"})
        resolver = Resolver(
            location_entity_groups=[[source]],
            template_scope_groups=[_template_registry(template)],
        )
        req = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.CLONE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        with pytest.raises(TypeError, match="uid"):
            resolver.resolve_requirement(req, _ctx=_ctx_with_seed(9))


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

    def test_from_ctx_prefers_new_scope_methods_when_both_exist(self) -> None:
        provider = Entity(label="provider")
        template = EntityTemplate(payload={"kind": Entity, "label": "templ"})
        ctx = SimpleNamespace(
            get_location_entity_groups=lambda: [[provider]],
            get_entity_groups=lambda: (_ for _ in ()).throw(AssertionError("legacy entity groups called")),
            get_template_scope_groups=lambda: [_template_registry(template)],
            get_template_groups=lambda: (_ for _ in ()).throw(AssertionError("legacy template groups called")),
        )

        resolver = Resolver.from_ctx(ctx)
        assert list(resolver.location_entity_groups)[0][0] is provider
        registry = list(resolver.template_scope_groups)[0]
        assert isinstance(registry, TemplateRegistry)
        assert registry.find_one(Selector(has_identifier="templ")) is template

    def test_from_ctx_legacy_entity_groups_warns(self) -> None:
        provider = Entity(label="provider")
        ctx = SimpleNamespace(
            get_entity_groups=lambda: [[provider]],
            get_template_scope_groups=lambda: [],
        )
        with pytest.deprecated_call(match="get_entity_groups"):
            resolver = Resolver.from_ctx(ctx)
        assert resolver.location_entity_groups

    def test_from_ctx_legacy_template_groups_warns(self) -> None:
        template = EntityTemplate(payload={"kind": Entity, "label": "templ"})
        ctx = SimpleNamespace(
            get_location_entity_groups=lambda: [],
            get_template_groups=lambda: [_template_registry(template)],
        )
        with pytest.deprecated_call(match="get_template_groups"):
            resolver = Resolver.from_ctx(ctx)
        assert resolver.template_scope_groups


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

    def test_resolve_dependency_prefers_linked_affordance_provider(self) -> None:
        g = Graph()
        frontier = _node(g, label="frontier")
        bob = _node(g, label="bob")
        _ = Affordance(
            registry=g,
            label="friend_here",
            predecessor_id=frontier.uid,
            successor_id=bob.uid,
            requirement=Requirement.from_identifier("bob"),
        )
        dep = _dependency(
            g,
            requirement=Requirement.from_identifier("bob"),
            predecessor_id=frontier.uid,
        )

        resolver = Resolver(entity_groups=[])
        success = resolver.resolve_dependency(dep)
        assert success is True
        assert dep.provider is bob

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

    def test_attachment_finalization_runs_for_scene_like_containers(self) -> None:
        g = Graph()
        cursor = _node(g, label="entry")
        dep = _dependency(
            g,
            requirement=Requirement(
                has_kind=TraversableNode,
                has_identifier="root.child.leaf",
                authored_path="root.child.leaf",
                is_qualified=True,
            ),
            predecessor_id=cursor.uid,
        )

        root_template = EntityTemplate(
            label="root",
            payload=FinalizableContainer(label="root"),
        )
        child_template = EntityTemplate(
            label="root.child",
            payload=FinalizableContainer(label="child"),
        )
        leaf_template = EntityTemplate(
            label="root.child.leaf",
            payload=TraversableNode(label="root.child.leaf"),
        )

        resolver = Resolver(
            location_entity_groups=[[cursor]],
            template_scope_groups=[_template_registry(leaf_template, root_template, child_template)],
        )
        ctx = SimpleNamespace(
            graph=g,
            cursor=cursor,
            cursor_id=cursor.uid,
            get_registries=lambda: [],
            get_inline_behaviors=lambda: [],
        )

        assert resolver.resolve_dependency(dep, _ctx=ctx) is True
        root = next((node for node in g.values() if isinstance(node, FinalizableContainer) and node.label == "root"), None)
        child = next((node for node in g.values() if isinstance(node, FinalizableContainer) and node.label == "child"), None)
        leaf = dep.provider

        assert root is not None
        assert child is not None
        assert leaf is not None
        assert root.finalize_calls >= 1
        assert child.finalize_calls >= 1
        assert root.source_id == child.uid
        assert root.sink_id == child.uid
        assert child.source_id == leaf.uid
        assert child.sink_id == leaf.uid


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
