"""Contract tests for ``tangl.vm.provision.resolver``.

Organized by concept:
- Offer gathering: FindProvisioner, TemplateProvisioner, StubProvisioner
- Requirement resolution: single vs ambiguous offers
- Dependency resolution: provider linking
- Frontier resolution: full node satisfaction check
"""

from __future__ import annotations

from random import Random
from types import SimpleNamespace
from uuid import UUID

import pytest

from tangl.core import (
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
from tangl.media.media_creators.svg_forge.vector_spec import VectorSpec
from tangl.media.media_resource import (
    MediaInventory,
    MediaResourceInventoryTag as MediaRIT,
    MediaResourceRegistry,
)
from tangl.story.story_graph import StoryGraph
from tangl.vm.provision import (
    Affordance,
    Dependency,
    Fanout,
    FindProvisioner,
    InlineTemplateProvisioner,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TemplateProvisioner,
    StubProvisioner,
    ProvisionOffer,
)
from tangl.vm.provision.matching import annotate_offer_specificity
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.causality import CausalityMode
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.traversable import TraversableNode


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


def _phase_ctx(
    *,
    graph: Graph,
    cursor: TraversableNode,
    step: int = 0,
    **kwargs,
) -> PhaseCtx:
    return PhaseCtx(graph=graph, cursor_id=cursor.uid, step=step, **kwargs)


class _ResolverCtx:
    def __init__(
        self,
        *,
        graph: Graph | None = None,
        cursor: TraversableNode | None = None,
        step: int = 0,
        meta: dict[str, object] | None = None,
        authorities: list[BehaviorRegistry] | None = None,
        rng: Random | None = None,
        location_entity_groups: list[list[object]] | None = None,
        template_scope_groups: list[TemplateRegistry] | None = None,
        token_catalogs: tuple[TokenCatalog, ...] = (),
        media_inventories: tuple[MediaInventory, ...] = (),
        causality_mode: CausalityMode | None = None,
    ) -> None:
        self.graph = graph
        self.cursor = cursor
        self.cursor_id = cursor.uid if cursor is not None else None
        self.step = step
        self.current_phase = ResolutionPhase.INIT
        self.correlation_id = None
        self.logger = None
        self.meta = dict(meta or {})
        self.selected_edge = None
        self.selected_payload = None
        self._authorities = list(authorities or [])
        self._rng = rng or Random(0)
        self._location_entity_groups = list(location_entity_groups or [])
        self._template_scope_groups = list(template_scope_groups or [])
        self._token_catalogs = tuple(token_catalogs)
        self._media_inventories = tuple(media_inventories)
        self.causality_mode = causality_mode

    def get_authorities(self):
        return list(self._authorities)

    def get_inline_behaviors(self):
        return []

    def get_random(self):
        return self._rng

    def get_meta(self):
        return dict(self.meta)

    def get_ns(self, node=None):
        _ = node
        return {}

    def get_location_entity_groups(self):
        return list(self._location_entity_groups)

    def get_template_scope_groups(self):
        return list(self._template_scope_groups)

    def get_token_catalogs(self, *, requirement=None):
        _ = requirement
        return list(self._token_catalogs)

    def get_media_inventories(self, *, requirement=None):
        _ = requirement
        return list(self._media_inventories)

    def derive(self, **kwargs):
        raise NotImplementedError


def _ctx_with_seed(seed: int) -> _ResolverCtx:
    return _ResolverCtx(rng=Random(seed))


def _ctx_with_token_catalogs(*catalogs: TokenCatalog) -> _ResolverCtx:
    return _ResolverCtx(token_catalogs=tuple(catalogs))


def _ctx_with_media_inventories(
    *inventories: MediaInventory,
    graph: Graph | None = None,
) -> _ResolverCtx:
    return _ResolverCtx(graph=graph, media_inventories=tuple(inventories))


def _phase_ctx_with_media_inventories(
    *,
    graph: Graph,
    cursor: TraversableNode,
    inventories: tuple[MediaInventory, ...],
) -> _ResolverCtx:
    return _ResolverCtx(
        graph=graph,
        cursor=cursor,
        media_inventories=inventories,
    )


def _template_registry(*templates: EntityTemplate) -> TemplateRegistry:
    registry = TemplateRegistry(label="resolver_test_templates")
    for template in templates:
        registry.add(template)
    return registry


def _media_inventory(label: str, *records: MediaRIT) -> MediaInventory:
    registry = MediaResourceRegistry(label=label)
    for record in records:
        registry.add(record)
    return MediaInventory(registry=registry, scope=label, label=label)


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
        assert leaf.templ_hash == template.content_hash()
        assert init.templ_hash == template.content_hash()
        assert intermediate.templ_hash == template.content_hash()

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

    def test_media_inventory_offers_follow_discovery_order(self, tmp_path) -> None:
        story_file = tmp_path / "story.svg"
        world_file = tmp_path / "world.svg"
        sys_file = tmp_path / "sys.svg"
        for item in (story_file, world_file, sys_file):
            item.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

        story_inventory = _media_inventory(
            "story",
            MediaRIT(path=story_file, label="poster.svg", tags={"scope:story"}),
        )
        world_inventory = _media_inventory(
            "world",
            MediaRIT(path=world_file, label="poster.svg", tags={"scope:world"}),
        )
        sys_inventory = _media_inventory(
            "sys",
            MediaRIT(path=sys_file, label="poster.svg", tags={"scope:sys"}),
        )

        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        req = Requirement(has_kind=MediaRIT, has_identifier="poster.svg")

        offers = resolver.gather_offers(
            req,
            _ctx=_ctx_with_media_inventories(story_inventory, world_inventory, sys_inventory),
        )

        assert offers
        assert getattr(offers[0].candidate, "path", None) == story_file

    def test_media_inventory_offers_respect_pinned_scope(self, tmp_path) -> None:
        story_file = tmp_path / "story.svg"
        sys_file = tmp_path / "sys.svg"
        for item in (story_file, sys_file):
            item.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

        story_inventory = _media_inventory(
            "story",
            MediaRIT(path=story_file, label="badge.svg", tags={"scope:story"}),
        )
        sys_inventory = _media_inventory(
            "sys",
            MediaRIT(path=sys_file, label="badge.svg", tags={"scope:sys"}),
        )

        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        req = Requirement(
            has_kind=MediaRIT,
            has_identifier="badge.svg",
            has_tags={"scope:sys"},
        )

        offers = resolver.gather_offers(
            req,
            _ctx=_ctx_with_media_inventories(story_inventory, sys_inventory),
        )

        assert offers
        assert getattr(offers[0].candidate, "path", None) == sys_file

    def test_gathers_from_entity_groups(self) -> None:
        e = Entity(label="sword")
        resolver = Resolver(entity_groups=[[e]])
        req = Requirement.from_identifier("sword")
        offers = resolver.gather_offers(req)
        assert len(offers) >= 1

    def test_empty_groups_yield_stub_offer_only_when_stubs_allowed(self) -> None:
        resolver = Resolver(entity_groups=[], template_groups=[])
        req = Requirement.from_identifier("missing")
        offers = resolver.gather_offers(req, allow_stubs=True)
        assert any(o.policy == ProvisionPolicy.STUB for o in offers)

        no_stub_offers = resolver.gather_offers(req, allow_stubs=False)
        assert no_stub_offers == []

    def test_hard_dirty_context_auto_allows_stub_offers(self) -> None:
        resolver = Resolver(entity_groups=[], template_groups=[])
        req = Requirement.from_identifier("missing")
        ctx = _ResolverCtx(
            causality_mode=CausalityMode.HARD_DIRTY,
        )
        offers = resolver.gather_offers(req, allow_stubs=False, _ctx=ctx)
        assert any(offer.policy == ProvisionPolicy.STUB for offer in offers)

    def test_stub_offer_not_selected_when_non_stub_offer_exists(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]], template_groups=[])
        req = Requirement.from_identifier("sword")
        offers = resolver.gather_offers(req, allow_stubs=True)
        assert len(offers) == 1
        assert all(o.policy != ProvisionPolicy.STUB for o in offers)

    def test_stub_offer_synthesizes_kind_and_identifier(self) -> None:
        class Person(Entity):
            pass

        resolver = Resolver(entity_groups=[], template_groups=[])
        req = Requirement(has_kind=Person, has_identifier="joe")
        provider = resolver.resolve_requirement(req, allow_stubs=True)
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

    def test_offer_annotation_requires_typed_provision_offer(self) -> None:
        req = Requirement(has_kind=Entity)

        with pytest.raises(AttributeError, match="candidate"):
            annotate_offer_specificity(req, SimpleNamespace())

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

    def test_gather_offers_includes_media_spec_create_offer_without_ctx(self) -> None:
        resolver = Resolver()
        req = Requirement(
            has_kind=MediaRIT,
            media_spec=VectorSpec(label="preview_banner"),
            provision_policy=ProvisionPolicy.ANY,
        )

        offers = resolver.gather_offers(req)

        assert len(offers) == 1
        assert offers[0].policy == ProvisionPolicy.CREATE

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
        source.templ_hash = b"refhash123"
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
        assert clone.templ_hash == b"refhash123"

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


class TestResolverFanout:
    def test_gather_fanout_offers_returns_all_matching_existing_in_stable_order(self) -> None:
        graph = Graph()
        near_a = _node(graph, label="near_a", tags={"menu"})
        near_b = _node(graph, label="near_b", tags={"menu"})
        far = _node(graph, label="far", tags={"menu"})
        resolver = Resolver(location_entity_groups=[[near_a, near_b], [far]], template_scope_groups=[])
        requirement = Requirement(has_kind=TraversableNode, has_tags={"menu"})

        offers = resolver.gather_fanout_offers(requirement)

        assert [offer.callback() for offer in offers] == [near_a, near_b, far]

    def test_gather_fanout_offers_includes_template_backed_traversables(self) -> None:
        graph = Graph()
        hub = _node(graph, label="scene")
        templ = EntityTemplate(
            label="scene.leaf",
            admission_scope="scene.*",
            payload=TraversableNode(label="leaf"),
        )
        resolver = Resolver(
            location_entity_groups=[[hub]],
            template_scope_groups=[_template_registry(templ)],
        )
        requirement = Requirement(
            has_kind=TraversableNode,
            has_identifier="scene.leaf",
            authored_path="scene.leaf",
            is_qualified=True,
        )
        ctx = _ResolverCtx(graph=graph, cursor=hub)

        offers = resolver.gather_fanout_offers(requirement, _ctx=ctx)

        assert len(offers) == 1
        assert offers[0].policy == ProvisionPolicy.CREATE
        assert offers[0].candidate is templ

    def test_gather_fanout_offers_excludes_token_and_stub_sources(self) -> None:
        class GearType(Singleton):
            pass

        GearType(label="torch")
        catalog = TokenCatalog(wst=GearType)
        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        requirement = Requirement(
            has_kind=GearType,
            has_identifier="torch",
            provision_policy=ProvisionPolicy.CREATE,
        )

        all_offers = resolver.gather_offers(
            requirement,
            allow_stubs=True,
            _ctx=_ctx_with_token_catalogs(catalog),
        )
        fanout_offers = resolver.gather_fanout_offers(
            requirement,
            _ctx=_ctx_with_token_catalogs(catalog),
        )

        assert any(bool(offer.policy & ProvisionPolicy.TOKEN) for offer in all_offers)
        assert fanout_offers == []

    def test_gather_fanout_offers_excludes_update_and_clone_sources(self) -> None:
        source = Entity(label="source")
        template = EntityTemplate(payload=Entity(label="patched"))
        resolver = Resolver(
            location_entity_groups=[[source]],
            template_scope_groups=[_template_registry(template)],
        )
        requirement = Requirement(
            has_kind=Entity,
            provision_policy=ProvisionPolicy.UPDATE | ProvisionPolicy.CLONE,
            reference_selector=Selector(has_identifier="source"),
            update_template_selector=Selector(has_identifier="patched"),
        )

        all_offers = resolver.gather_offers(requirement)
        fanout_offers = resolver.gather_fanout_offers(requirement)

        assert any(bool(offer.policy & ProvisionPolicy.UPDATE) for offer in all_offers)
        assert any(bool(offer.policy & ProvisionPolicy.CLONE) for offer in all_offers)
        assert fanout_offers
        assert all(not bool(offer.policy & ProvisionPolicy.UPDATE) for offer in fanout_offers)
        assert all(not bool(offer.policy & ProvisionPolicy.CLONE) for offer in fanout_offers)

    def test_resolve_fanout_creates_one_affordance_per_provider(self) -> None:
        graph = Graph()
        hub = _node(graph, label="hub")
        alpha = _node(graph, label="alpha", tags={"menu"})
        beta = _node(graph, label="beta", tags={"menu"})
        fanout = Fanout(
            registry=graph,
            predecessor_id=hub.uid,
            requirement=Requirement(has_kind=TraversableNode, has_tags={"menu"}),
        )
        resolver = Resolver(location_entity_groups=[[alpha, beta]], template_scope_groups=[])

        providers = resolver.resolve_fanout(fanout)

        affordances = [
            affordance
            for affordance in hub.edges_out(Selector(has_kind=Affordance))
            if "fanout" in (getattr(affordance, "tags", set()) or set())
        ]
        assert providers == [alpha, beta]
        assert fanout.providers == [alpha, beta]
        assert [affordance.successor for affordance in affordances] == [alpha, beta]

    def test_resolve_fanout_refresh_removes_stale_affordances(self) -> None:
        graph = Graph()
        hub = _node(graph, label="hub")
        alpha = _node(graph, label="alpha", tags={"menu"})
        beta = _node(graph, label="beta", tags={"menu"})
        fanout = Fanout(
            registry=graph,
            predecessor_id=hub.uid,
            requirement=Requirement(has_kind=TraversableNode, has_tags={"menu"}),
        )

        Resolver(location_entity_groups=[[alpha, beta]], template_scope_groups=[]).resolve_fanout(fanout)
        Resolver(location_entity_groups=[[beta]], template_scope_groups=[]).resolve_fanout(fanout)

        affordances = [
            affordance
            for affordance in hub.edges_out(Selector(has_kind=Affordance))
            if "fanout" in (getattr(affordance, "tags", set()) or set())
        ]
        assert fanout.providers == [beta]
        assert len(affordances) == 1
        assert affordances[0].successor is beta


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
        # EXISTING-only policy filters out STUB offers.
        assert provider is None
        assert req.unsatisfiable is True
        assert req.resolution_reason == "no_offers"

    def test_allow_stubs_with_existing_offer_prefers_existing(self) -> None:
        sword = Entity(label="sword")
        resolver = Resolver(entity_groups=[[sword]])
        req = Requirement.from_identifier("sword")
        provider = resolver.resolve_requirement(req, allow_stubs=True)
        assert provider is sword
        assert req.selected_offer_policy == ProvisionPolicy.EXISTING

    def test_from_ctx_requires_provision_context_shape(self) -> None:
        ctx = SimpleNamespace()
        with pytest.raises(TypeError, match="get_location_entity_groups"):
            Resolver.from_ctx(ctx)

    def test_invalid_resolve_override_sets_override_reason(self) -> None:
        def bad_override(*, caller, offers, ctx, **kw):
            return ["not-an-offer"]

        local_registry = BehaviorRegistry(label="test_resolve_req_registry")
        local_registry.register(func=bad_override, task="resolve_req")
        ctx = _ResolverCtx(authorities=[local_registry])
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
        ctx = _ResolverCtx(
            location_entity_groups=[[provider]],
            template_scope_groups=[_template_registry(template)],
        )

        resolver = Resolver.from_ctx(ctx)
        assert list(resolver.location_entity_groups)[0][0] is provider
        registry = list(resolver.template_scope_groups)[0]
        assert isinstance(registry, TemplateRegistry)
        assert registry.find_one(Selector(has_identifier="templ")) is template


class TestResolverNodeContext:
    def test_make_node_ctx_derives_from_phase_ctx(self) -> None:
        parent_graph = Graph()
        parent = _node(parent_graph, label="parent")
        child_graph = Graph()
        child = _node(child_graph, label="child")
        parent_ctx = _phase_ctx(
            graph=parent_graph,
            cursor=parent,
            step=7,
            current_phase=ResolutionPhase.UPDATE,
            correlation_id="corr-1",
            meta={"source": "parent"},
            incoming_payload={"kind": "payload"},
        )

        node_ctx = Resolver()._make_node_ctx(
            graph=child_graph,
            node=child,
            _ctx=parent_ctx,
            request_ctx_path="story.child",
        )

        assert isinstance(node_ctx, PhaseCtx)
        assert node_ctx is not parent_ctx
        assert node_ctx.graph is child_graph
        assert node_ctx.cursor_id == child.uid
        assert node_ctx.step == 7
        assert node_ctx.current_phase is ResolutionPhase.INIT
        assert node_ctx.correlation_id == "corr-1"
        assert node_ctx.meta == {
            "source": "parent",
            "request_ctx_path": "story.child",
        }
        assert node_ctx.random is parent_ctx.random

    def test_make_node_ctx_derives_from_phase_ctx_for_story_graph(self) -> None:
        graph = StoryGraph()
        source = TraversableNode(label="source")
        child = TraversableNode(label="child")
        graph.add(source)
        graph.add(child)
        prelink_ctx = PhaseCtx(
            graph=graph,
            cursor_id=source.uid,
            correlation_id="prelink-1",
            meta={"phase": "prelink"},
        )

        node_ctx = Resolver()._make_node_ctx(
            graph=graph,
            node=child,
            _ctx=prelink_ctx,
            request_ctx_path="story.child",
        )

        assert isinstance(node_ctx, PhaseCtx)
        assert node_ctx.graph is graph
        assert node_ctx.cursor_id == child.uid
        assert node_ctx.step == 0
        assert node_ctx.correlation_id == "prelink-1"
        assert node_ctx.meta == {
            "phase": "prelink",
            "request_ctx_path": "story.child",
        }

    def test_make_node_ctx_rejects_unsupported_context(self) -> None:
        graph = Graph()
        node = _node(graph, label="child")
        bad_ctx = SimpleNamespace(
            graph=graph,
            cursor_id=node.uid,
            step=3,
            correlation_id="bad",
            meta={"phase": "bad"},
            get_authorities=lambda: [],
            get_inline_behaviors=lambda: [],
            get_location_entity_groups=lambda: [[node]],
            get_template_scope_groups=lambda: [],
        )

        with pytest.raises(AttributeError, match="derive"):
            Resolver()._make_node_ctx(
                graph=graph,
                node=node,
                _ctx=bad_ctx,
                request_ctx_path="story.child",
            )


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
        ctx = _phase_ctx(graph=g, cursor=node, step=3)

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

    def test_resolve_dependency_binds_media_inventory_provider_into_graph(self, tmp_path) -> None:
        asset = tmp_path / "cover.svg"
        asset.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

        inventory = _media_inventory(
            "world",
            MediaRIT(path=asset, label="cover.svg", tags={"scope:world"}),
        )
        graph = Graph()
        node = _node(graph, label="start")
        dep = _dependency(
            graph,
            requirement=Requirement(has_kind=MediaRIT, has_identifier="cover.svg"),
            predecessor_id=node.uid,
        )

        resolver = Resolver(location_entity_groups=[], template_scope_groups=[])
        success = resolver.resolve_dependency(
            dep,
            _ctx=_phase_ctx_with_media_inventories(
                graph=graph,
                cursor=node,
                inventories=(inventory,),
            ),
        )

        assert success is True
        assert isinstance(dep.provider, MediaRIT)
        assert dep.provider is not None
        assert dep.provider.registry is graph
        assert dep.provider.path == asset

    def test_stub_offer_bypasses_requirement_validation(self) -> None:
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
        ctx = _phase_ctx(graph=g, cursor=node, step=11)
        success = resolver.resolve_dependency(dep, allow_stubs=True, _ctx=ctx)
        assert success is True
        assert dep.provider is not None
        assert isinstance(dep.provider, Person)
        assert dep.satisfied
        assert dep.requirement.selected_offer_policy == ProvisionPolicy.STUB
        assert dep.requirement.resolved_step == 11
        assert dep.requirement.resolved_cursor_id == node.uid

    def test_stub_offer_requires_allow_stubs_or_hard_dirty(self) -> None:
        class Person(RegistryAware):
            pass

        g = Graph()
        node = _node(g, label="room")
        dep = _dependency(
            g,
            requirement=Requirement(has_kind=Person, has_identifier="joe"),
            predecessor_id=node.uid,
        )

        provider = Person(label="joe")
        selected_offer = ProvisionOffer(
            origin_id="stub-test",
            policy=ProvisionPolicy.STUB,
            callback=lambda *_, **__: provider,
        )

        class _Resolver(Resolver):
            def _resolve_requirement_offer(  # noqa: D401 - test seam override
                self,
                requirement,
                *,
                allow_stubs=False,
                preferred_offers=(),
                _ctx=None,
            ):
                requirement.selected_offer_policy = ProvisionPolicy.STUB
                requirement.resolution_reason = "resolved"
                requirement.resolution_meta = {"selected": {"origin_id": "stub-test"}}
                return provider, selected_offer, [selected_offer]

        resolver = _Resolver(entity_groups=[], template_groups=[])
        with pytest.raises(AssertionError, match="STUB offer selected"):
            resolver.resolve_dependency(dep, allow_stubs=False)

    def test_stub_offer_escalates_hard_dirty_callback(self) -> None:
        class Person(RegistryAware):
            pass

        g = Graph()
        node = _node(g, label="room")
        dep = _dependency(
            g,
            requirement=Requirement(has_kind=Person, has_identifier="joe"),
            predecessor_id=node.uid,
        )

        transitions: list[tuple[str, str | None]] = []

        def _escalate(reason: str, step_id: str | None = None) -> bool:
            transitions.append((reason, step_id))
            return True

        ctx = _phase_ctx(
            graph=g,
            cursor=node,
            step=11,
            escalate_to_hard_dirty_callback=_escalate,
        )
        resolver = Resolver(entity_groups=[], template_groups=[])
        assert resolver.resolve_dependency(dep, allow_stubs=True, _ctx=ctx) is True
        assert transitions == [("stub_link_accepted", str(dep.uid))]
        assert dep.requirement.resolution_reason == "stub_link_resolved"

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
        ctx = _phase_ctx(graph=g, cursor=cursor)

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

    def test_node_with_empty_fanout_still_resolves_true(self) -> None:
        g = Graph()
        node = _node(g, label="hub")
        Fanout(
            registry=g,
            predecessor_id=node.uid,
            requirement=Requirement(has_kind=TraversableNode, has_tags={"menu"}),
        )

        resolver = Resolver(entity_groups=[], template_groups=[])
        assert resolver.resolve_frontier_node(node) is True
