"""Path-scope provisioning contract tests for vm38.

Covers:
- Pure scope/path utilities (admission, distance, build-plan)
- TemplateProvisioner scope policy fork for qualified/unqualified episodes
- Offer sort behavior with scope distance
- Resolver preview and executor add-then-bind semantics
"""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core38 import EntityTemplate, Graph, TemplateRegistry
from tangl.vm38.provision import (
    ProvisionOffer,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TemplateProvisioner,
    admitted,
    build_plan,
    resolve_target_path,
    scope_distance,
    target_context_candidates,
)
from tangl.vm38.traversable import TraversableNode
from tangl.vm38 import Dependency


def _ctx(*, graph: Graph, cursor: TraversableNode) -> SimpleNamespace:
    return SimpleNamespace(
        graph=graph,
        cursor=cursor,
        cursor_id=cursor.uid,
        step=0,
        get_authorities=lambda: [],
        get_registries=lambda: [],
        get_inline_behaviors=lambda: [],
    )


def _template_registry(*templates: EntityTemplate) -> TemplateRegistry:
    registry = TemplateRegistry(label="scope_test_templates")
    for template in templates:
        registry.add(template)
    return registry


class TestScopeAdmission:
    def test_universal_and_prefix_scope_admission(self) -> None:
        assert admitted(None, "castle.guard")
        assert admitted("*", "castle.guard")
        assert admitted("castle.*", "castle.guard")
        assert admitted("castle.*", "castle.morning.guard")
        assert not admitted("castle.*", "village.guard")

    def test_brace_expansion_admission(self) -> None:
        assert admitted("scene{2,10}.*", "scene2.entry")
        assert admitted("scene{2,10}.*", "scene10.entry")
        assert not admitted("scene{2,10}.*", "scene3.entry")


class TestScopeDistance:
    def test_scope_distance_values(self) -> None:
        assert scope_distance("castle.*", "castle.guard") == 0
        assert scope_distance("castle.*", "castle.morning.guard") == 1
        assert scope_distance("*", "anything.here") == 0
        assert scope_distance("castle.*", "village.guard") == 1


class TestBuildPlan:
    def test_build_plan_uses_segment_zero_top_level_anchor(self) -> None:
        graph = Graph()
        castle = TraversableNode(label="castle", registry=graph)
        morning = TraversableNode(label="morning", registry=graph)
        castle.add_child(morning)

        assert build_plan("castle.morning.gatehouse", graph) == []
        assert build_plan("castle.keep.gatehouse", graph) == ["keep"]

    def test_build_plan_returns_missing_prefix_chain_in_order(self) -> None:
        graph = Graph()
        assert build_plan("castle.morning.gatehouse", graph) == ["castle", "morning"]


class TestResolveTargetPath:
    def test_absolute_single_segment_identifier_is_not_reanchored(self) -> None:
        resolved = resolve_target_path(
            identifier="scene2",
            request_ctx="scene1.block1",
            is_absolute=True,
        )
        assert resolved == "scene2"


class TestTargetContextCandidates:
    def test_relative_bare_generates_ancestor_candidates(self) -> None:
        assert target_context_candidates(
            identifier="entry",
            request_ctx="scene1.block1",
        ) == [
            "scene1.block1.entry",
            "scene1.entry",
            "entry",
        ]

    def test_dotted_identifier_keeps_single_candidate(self) -> None:
        assert target_context_candidates(
            identifier="scene2.entry",
            request_ctx="scene1.block1",
        ) == ["scene2.entry"]

    def test_absolute_single_segment_keeps_single_candidate(self) -> None:
        assert target_context_candidates(
            identifier="scene2",
            request_ctx="scene1.block1",
            is_absolute=True,
        ) == ["scene2"]


class TestTemplateProvisionerScopePolicy:
    def test_unqualified_episode_prefers_zero_distance_candidate(self) -> None:
        template = EntityTemplate(
            label="castle.morning.gatehouse",
            payload=TraversableNode(label="gatehouse"),
            admission_scope="castle.*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="gatehouse",
            authored_path="gatehouse",
            is_qualified=False,
        )
        provisioner = TemplateProvisioner(
            registries=[_template_registry(template)],
            request_ctx="castle.morning",
            graph=Graph(),
        )
        offers = list(provisioner.get_dependency_offers(req))
        assert len(offers) == 1
        assert offers[0].scope_distance == 0
        assert offers[0].target_ctx == "castle.gatehouse"

    def test_qualified_episode_emits_build_plan_and_scope_distance(self) -> None:
        template = EntityTemplate(
            label="castle.morning.gatehouse",
            payload=TraversableNode(label="gatehouse"),
            admission_scope="castle.*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="castle.morning.gatehouse",
            authored_path="castle.morning.gatehouse",
            is_qualified=True,
        )
        provisioner = TemplateProvisioner(
            registries=[_template_registry(template)],
            request_ctx="village.square",
            graph=Graph(),
        )
        offers = list(provisioner.get_dependency_offers(req))
        assert len(offers) == 1
        assert offers[0].scope_distance == 1
        assert offers[0].build_plan == ["castle", "morning"]

    def test_admission_rejection_filters_offer(self) -> None:
        template = EntityTemplate(
            label="gatehouse",
            payload=TraversableNode(label="gatehouse"),
            admission_scope="castle.*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="gatehouse",
            authored_path="gatehouse",
            is_qualified=False,
        )
        provisioner = TemplateProvisioner(
            registries=[_template_registry(template)],
            request_ctx="village",
            graph=Graph(),
        )
        assert list(provisioner.get_dependency_offers(req)) == []

    def test_qualified_path_uses_target_ctx_for_scope_filtering(self) -> None:
        template_scene1 = EntityTemplate(
            label="scene1.entry",
            payload=TraversableNode(label="entry"),
            admission_scope="scene1.*",
        )
        template_scene2 = EntityTemplate(
            label="scene2.entry",
            payload=TraversableNode(label="entry"),
            admission_scope="scene2.*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="scene2.entry",
            authored_path="scene2.entry",
            is_qualified=True,
        )
        provisioner = TemplateProvisioner(
            registries=[_template_registry(template_scene1, template_scene2)],
            request_ctx="scene1.start",
            graph=Graph(),
        )

        offers = list(provisioner.get_dependency_offers(req))
        assert len(offers) == 1
        assert offers[0].target_ctx == "scene2.entry"
        assert offers[0].build_plan == ["scene2"]

    def test_qualified_identifier_does_not_fallback_to_leaf_template_identity(self) -> None:
        template = EntityTemplate(
            label="entry",
            payload=TraversableNode(label="entry"),
            admission_scope="scene2.*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="scene2.entry",
            authored_path="scene2.entry",
            is_qualified=True,
        )
        provisioner = TemplateProvisioner(
            registries=[_template_registry(template)],
            request_ctx="scene1.start",
            graph=Graph(),
        )

        offers = list(provisioner.get_dependency_offers(req))
        assert offers == []


class TestOfferSortKey:
    def test_scope_distance_beats_caller_distance(self) -> None:
        close_scope = ProvisionOffer(
            origin_id="scope-close",
            policy=ProvisionPolicy.CREATE,
            callback=lambda *_, **__: None,
            scope_distance=0,
            distance_from_caller=9,
        )
        far_scope = ProvisionOffer(
            origin_id="scope-far",
            policy=ProvisionPolicy.CREATE,
            callback=lambda *_, **__: None,
            scope_distance=1,
            distance_from_caller=0,
        )
        assert close_scope.sort_key() < far_scope.sort_key()

    def test_legacy_distance_order_unchanged_when_scope_distance_is_zero(self) -> None:
        near = ProvisionOffer(
            origin_id="near",
            policy=ProvisionPolicy.CREATE,
            callback=lambda *_, **__: None,
            scope_distance=0,
            distance_from_caller=0,
        )
        far = ProvisionOffer(
            origin_id="far",
            policy=ProvisionPolicy.CREATE,
            callback=lambda *_, **__: None,
            scope_distance=0,
            distance_from_caller=3,
        )
        assert near.sort_key() < far.sort_key()


class TestResolverPreviewAndExecution:
    def test_preview_reports_viable_chain(self) -> None:
        graph = Graph()
        cursor = TraversableNode(label="entry", registry=graph)
        leaf = EntityTemplate(
            label="castle.gatehouse",
            payload=TraversableNode(label="gatehouse"),
            admission_scope="castle.*",
        )
        castle = EntityTemplate(
            label="castle",
            payload=TraversableNode(label="castle"),
            admission_scope="*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="castle.gatehouse",
            authored_path="castle.gatehouse",
            is_qualified=True,
        )
        resolver = Resolver(template_scope_groups=[_template_registry(leaf, castle)])
        before = len(graph)
        preview = resolver.preview_requirement(req, _ctx=_ctx(graph=graph, cursor=cursor))
        assert preview.viable is True
        assert preview.chain == ["castle"]
        assert len(graph) == before

    def test_preview_reports_chain_unresolvable(self) -> None:
        graph = Graph()
        cursor = TraversableNode(label="entry", registry=graph)
        leaf = EntityTemplate(
            label="castle.gatehouse",
            payload=TraversableNode(label="gatehouse"),
            admission_scope="castle.*",
        )
        req = Requirement(
            has_kind=TraversableNode,
            has_identifier="castle.gatehouse",
            authored_path="castle.gatehouse",
            is_qualified=True,
        )
        resolver = Resolver(template_scope_groups=[_template_registry(leaf)])
        preview = resolver.preview_requirement(req, _ctx=_ctx(graph=graph, cursor=cursor))
        assert preview.viable is False
        assert preview.blockers
        assert preview.blockers[0].reason == "chain_unresolvable"

    def test_executor_adds_then_binds_and_stamps_templ_hash(self) -> None:
        graph = Graph()
        source = TraversableNode(label="source", registry=graph)
        dep = Dependency(
            registry=graph,
            predecessor_id=source.uid,
            requirement=Requirement(has_identifier="crafted"),
        )
        template = EntityTemplate(
            label="crafted",
            payload=TraversableNode(label="crafted"),
        )
        resolver = Resolver(template_scope_groups=[_template_registry(template)])
        ctx = _ctx(graph=graph, cursor=source)

        assert resolver.resolve_dependency(dep, _ctx=ctx) is True
        assert dep.satisfied is True
        assert dep.provider is not None
        assert dep.provider.registry is graph
        assert dep.provider.templ_hash == template.content_hash().hex()

    def test_provider_rejected_keeps_added_provider_as_invariant_safety_net(self) -> None:
        graph = Graph()
        source = TraversableNode(label="source", registry=graph)
        dep = Dependency(
            registry=graph,
            predecessor_id=source.uid,
            requirement=Requirement(has_identifier="expected"),
        )
        bad_provider = TraversableNode(label="wrong")
        bad_offer = ProvisionOffer(
            origin_id="bad",
            policy=ProvisionPolicy.CREATE,
            callback=lambda *_, **__: bad_provider,
        )

        class _Resolver(Resolver):
            def _resolve_requirement_offer(self, requirement, *, force=False, preferred_offers=(), _ctx=None):
                requirement.selected_offer_policy = ProvisionPolicy.CREATE
                requirement.resolution_reason = "resolved"
                requirement.resolution_meta = {"selected": {"origin_id": "bad"}}
                return bad_provider, bad_offer, [bad_offer]

        resolver = _Resolver(template_scope_groups=[])
        ctx = _ctx(graph=graph, cursor=source)

        assert resolver.resolve_dependency(dep, _ctx=ctx) is False
        assert dep.requirement.resolution_reason == "provider_rejected"
        assert bad_provider.registry is graph
