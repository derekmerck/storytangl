"""Tests for qualified identifier lookups in provisioning.

Organized by functionality:
- Strict path matching precedence.
- Location-based fallback when scope patterns apply.
- Global-only guardrails and provenance tracking.
"""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core.factory import HierarchicalTemplate, TemplateFactory
from tangl.core.graph import Graph, Node
from tangl.vm.provision import (
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


# ============================================================================
# Helpers
# ============================================================================


def _ctx(graph: Graph, cursor: Node | None = None) -> SimpleNamespace:
    cursor_id = cursor.uid if cursor is not None else None
    return SimpleNamespace(graph=graph, cursor=cursor, cursor_id=cursor_id)


# ============================================================================
# Qualified identifier resolution
# ============================================================================


class TestQualifiedIdentifierLocationLookup:
    """Tests for two-stage qualified identifier resolution."""

    def test_stage1_strict_path_wins(self) -> None:
        """Strict path lookup should take priority over scope matches."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        exact_template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            tags={"exact"},
        )
        root = HierarchicalTemplate(label="scene1", children={"shop": exact_template})
        factory.add(root.children["shop"])

        scoped_template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            path_pattern="scene1.*",
            tags={"scoped"},
        )
        factory.add(scoped_template)

        requirement = Requirement(
            graph=graph,
            template_ref="scene1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        ctx = _ctx(graph)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert len(offers) == 1
        provider = offers[0].accept(ctx=ctx)
        assert "exact" in provider.tags
        assert "scoped" not in provider.tags

    def test_stage2_location_based_with_scope(self) -> None:
        """Location-based matching should resolve scoped qualified refs."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            path_pattern="scene1.*",
            tags={"scoped"},
        )
        factory.add(template)

        scene1 = graph.add_subgraph(label="scene1")
        cursor = graph.add_node(label="start")
        scene1.add_member(cursor)

        requirement = Requirement(
            graph=graph,
            template_ref="scene1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        ctx = _ctx(graph, cursor)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert len(offers) == 1
        provider = offers[0].accept(ctx=ctx)
        assert "scoped" in provider.tags

    def test_stage2_rejects_global_only_template(self) -> None:
        """Global-only templates should not match qualified refs."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            path_pattern="*",
            tags={"global"},
        )
        factory.add(template)

        cursor = graph.add_node(label="start")

        requirement = Requirement(
            graph=graph,
            template_ref="book1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        ctx = _ctx(graph, cursor)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert offers == []

    def test_stage2_without_context_fails_gracefully(self) -> None:
        """Qualified refs without context should not resolve scope matches."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            path_pattern="scene1.*",
        )
        factory.add(template)

        requirement = Requirement(
            graph=graph,
            template_ref="scene1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        ctx = _ctx(graph, cursor=None)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert offers == []

    def test_provenance_tracking_stage1(self) -> None:
        """Provenance should indicate strict path resolution."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        exact_template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
        )
        root = HierarchicalTemplate(label="scene1", children={"shop": exact_template})
        factory.add(root.children["shop"])

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        requirement = Requirement(
            graph=graph,
            template_ref="scene1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        ctx = _ctx(graph, cursor=None)

        resolved, provenance = provisioner._resolve_template(requirement, ctx=ctx)

        assert resolved == exact_template
        assert provenance["lookup_method"] == "strict_path"

    def test_provenance_tracking_stage2(self) -> None:
        """Provenance should indicate location-based resolution."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            path_pattern="scene1.*",
        )
        factory.add(template)

        scene1 = graph.add_subgraph(label="scene1")
        cursor = graph.add_node(label="start")
        scene1.add_member(cursor)

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        requirement = Requirement(
            graph=graph,
            template_ref="scene1.shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        ctx = _ctx(graph, cursor=cursor)

        resolved, provenance = provisioner._resolve_template(requirement, ctx=ctx)

        assert resolved == template
        assert provenance["lookup_method"] == "location_based"
        assert "location_score" in provenance


class TestUnqualifiedIdentifierLookup:
    """Tests for unqualified identifier lookups."""

    def test_unqualified_uses_label_lookup(self) -> None:
        """Unqualified refs should use label lookup."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
        )
        factory.add(template)

        requirement = Requirement(
            graph=graph,
            template_ref="shop",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )

        provisioner = TemplateProvisioner(factory=factory, layer="author")
        ctx = _ctx(graph, cursor=None)

        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert len(offers) == 1
        provider = offers[0].accept(ctx=ctx)
        assert provider.label == "shop"
