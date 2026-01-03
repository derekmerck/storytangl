"""Tests for address-driven template lookup and namespace creation.

Organized by functionality:
- Qualified references: strict matching without tail fallbacks.
- Namespace creation: address prefixes create container hierarchy.
- Scope selection: templates ranked by scope specificity.
- Eager materialization: only declared instances appear in full builds.
"""

from __future__ import annotations

from tangl.core.factory import HierarchicalTemplate, TemplateFactory
from tangl.core.graph import Graph, Node
from .conftest import build_world


# ============================================================================
# Qualified reference resolution
# ============================================================================

class TestQualifiedReferenceResolution:
    """Tests for strict matching of qualified template identifiers."""

    def test_qualified_identifier_no_tail_fallback(self) -> None:
        """Qualified identifiers should not silently fall back to tails."""

        factory = TemplateFactory(label="test")
        factory.add(HierarchicalTemplate(label="shop", obj_cls=Node))

        result = factory.find_one(path="book1.ch1.shop")

        assert result is None


# ============================================================================
# Namespace creation
# ============================================================================

class TestNamespaceCreation:
    """Tests for top-down namespace container creation from addresses."""

    def test_ensure_namespace_creates_prefix_containers(self) -> None:
        """Ensure that prefixes are materialized as containers."""

        from tangl.story.fabula.address_resolver import ensure_namespace

        graph = Graph(label="test")

        ensure_namespace(graph, "a.b.c")

        assert graph.find_subgraph(label="a") is not None
        assert graph.find_subgraph(label="b") is not None
        assert graph.find_subgraph(label="c") is None

        b = graph.find_subgraph(label="b")
        assert b is not None
        assert b.parent is not None
        assert b.parent.label == "a"


# ============================================================================
# Scope-aware template selection
# ============================================================================

class TestScopeRankTemplateSelection:
    """Tests for scope-ranked template resolution against an address."""

    def test_template_selection_by_scope_rank(self) -> None:
        """Resolve the most specific template for an anchored address."""

        from tangl.story.fabula.address_resolver import resolve_template_for_address

        factory = TemplateFactory(label="test")
        global_guard = HierarchicalTemplate(
            label="guard",
            obj_cls=Node,
            path_pattern="*",
            declares_instance=True,
        )
        scene_guard = HierarchicalTemplate(
            label="scene_guard",
            obj_cls=Node,
            path_pattern="scene1.*",
            declares_instance=True,
        )
        factory.add(global_guard)
        factory.add(scene_guard)

        graph = Graph(label="test")
        scene1 = graph.add_subgraph(label="scene1")
        anchor = graph.add_node(label="start")
        scene1.add_member(anchor)

        result = resolve_template_for_address(
            factory,
            address="scene1.start",
            selector=anchor,
        )

        assert result == scene_guard


# ============================================================================
# Eager materialization scope
# ============================================================================

class TestEagerMaterialization:
    """Tests for eager materialization behavior and template filtering."""

    def test_eager_mode_only_instantiates_declared_instances(self) -> None:
        """Eager mode should not auto-instantiate archetype templates."""

        script = {
            "label": "test",
            "metadata": {
                "title": "Test",
                "author": "Tests",
                "start_at": "scene1.start",
            },
            "templates": {
                "guard": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                    "label": "guard",
                }
            },
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "start": {
                            "obj_cls": "tangl.story.episode.block.Block",
                            "content": "Begin",
                        }
                    },
                }
            },
        }

        world = build_world(script)
        graph = world.create_story("test", mode="full")

        assert graph.find_node(label="start") is not None
        assert graph.find_node(label="guard") is None
