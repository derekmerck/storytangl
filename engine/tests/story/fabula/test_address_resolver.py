"""Tests for address-driven resolution helpers.

Organized by functionality:
- Template resolution by scope pattern.
- Namespace prefix creation.
- Address-based instance materialization.
"""

from __future__ import annotations

import pytest

from tangl.core.factory import HierarchicalTemplate, Template, TemplateFactory
from tangl.core.graph import Graph, Node, Subgraph
from tangl.story.episode.block import Block
from tangl.story.fabula.address_resolver import (
    _get_prefixes,
    _template_path_matches_address,
    ensure_instance,
    ensure_namespace,
    iter_matching_templates,
    resolve_template_for_address,
)
from tangl.story.story_graph import StoryGraph
from .conftest import build_world, create_minimal_world


# ============================================================================
# Template resolution
# ============================================================================

class TestResolveTemplateForAddress:
    """Tests for selecting templates by address and scope."""

    def test_resolve_template_for_address_finds_scoped_template(self) -> None:
        """Resolve templates based on scope patterns and addresses."""

        factory = TemplateFactory(label="test")
        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            path_pattern="scene1.*",
            declares_instance=True,
        )
        factory.add(template)

        result = resolve_template_for_address(
            factory,
            "scene1.shop",
            strict=True,
        )

        assert result == template

    def test_exact_path_match_requires_equality(self) -> None:
        """Template paths must exactly match the address."""

        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
        )
        scene = HierarchicalTemplate(label="scene1", children={"shop": template})
        root = HierarchicalTemplate(label="story", children={"scene1": scene})
        resolved_template = root.children["scene1"].children["shop"]

        assert _template_path_matches_address(resolved_template, "story.scene1.shop") is True
        assert _template_path_matches_address(resolved_template, "shop") is False
        assert _template_path_matches_address(resolved_template, "scene1.shop") is False
        assert _template_path_matches_address(resolved_template, "other.scene1.shop") is False

    def test_resolve_does_not_exact_match_on_suffix(self) -> None:
        """Suffix-only addresses should not trigger exact-match logic."""

        factory = TemplateFactory(label="test")
        template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
        )
        scene = HierarchicalTemplate(label="scene1", children={"shop": template})
        root = HierarchicalTemplate(label="story", children={"scene1": scene})
        resolved_template = root.children["scene1"].children["shop"]
        factory.add(resolved_template)

        result = resolve_template_for_address(
            factory,
            "shop",
            strict=False,
        )

        assert result is None

    def test_iter_matching_templates_prefers_exact_matches(self) -> None:
        """Exact path matches should short-circuit scope matches."""

        exact_template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
        )
        scoped_template = HierarchicalTemplate(
            label="shop",
            obj_cls=Node,
            declares_instance=True,
            path_pattern="scene1.*",
        )
        scene = HierarchicalTemplate(label="scene1", children={"shop": exact_template})
        root = HierarchicalTemplate(label="story", children={"scene1": scene})

        factory = TemplateFactory(label="test")
        factory.add(root.children["scene1"].children["shop"])
        factory.add(scoped_template)

        matches = list(
            iter_matching_templates(
                factory,
                "story.scene1.shop",
            )
        )

        assert matches == [(exact_template, -1.0, True)]


# ============================================================================
# Namespace creation
# ============================================================================

class TestEnsureNamespace:
    """Tests for namespace prefix creation."""

    def test_ensure_namespace_creates_prefix_chain(self) -> None:
        """Ensure parent containers are created in order."""

        graph = Graph(label="test")

        result = ensure_namespace(graph, "a.b.c")

        a = graph.find_subgraph(path="a")
        b = graph.find_subgraph(path="a.b")
        c = graph.find_subgraph(path="a.b.c")

        assert a is not None
        assert b is not None
        assert b.parent == a
        assert c is None
        assert result == b

    def test_get_prefixes_excludes_leaf(self) -> None:
        """Prefixes should not include the full address."""

        assert _get_prefixes("a.b.c") == ["a", "a.b"]
        assert _get_prefixes("a.b") == ["a"]
        assert _get_prefixes("a") == []

    def test_ensure_namespace_attaches_once(self) -> None:
        """Containers should be attached to parent OR graph, not both."""

        graph = Graph(label="test")

        ensure_namespace(graph, "a.b.c")

        a = graph.find_subgraph(label="a")
        b = graph.find_subgraph(label="b")

        assert a is not None
        assert b is not None
        assert a in graph.subgraphs
        assert b in a.members
        assert a.parent is None
        assert b.parent == a


# ============================================================================
# Instance materialization
# ============================================================================

class TestEnsureInstance:
    """Tests for typed instance materialization at an address."""

    def test_ensure_instance_materializes_typed_node(self) -> None:
        """Ensure instances are created with typed templates and namespace parents."""

        factory = TemplateFactory(label="test")
        template = HierarchicalTemplate(
            label="start",
            obj_cls=Block,
            path_pattern="*",
            declares_instance=True,
        )
        factory.add(template)

        world = build_world(
            {
                "label": "test",
                "metadata": {"title": "Test", "author": "Tests"},
                "scenes": {},
            }
        )
        graph = StoryGraph(label="test", world=world)

        result = ensure_instance(
            graph,
            "scene1.start",
            factory,
            world=world,
        )

        assert isinstance(result, Block)
        assert result.label == "start"

        scene1 = graph.find_subgraph(path="scene1")
        assert scene1 is not None
        assert result.parent == scene1

    def test_ensure_instance_no_duplicate_containers(self) -> None:
        """Ensure container namespaces are reused instead of duplicated."""

        factory = TemplateFactory(label="test")
        template = HierarchicalTemplate(
            label="start",
            obj_cls=Block,
            path_pattern="*",
            declares_instance=True,
        )
        factory.add(template)

        graph = Graph(label="test")
        world = create_minimal_world()

        instance1 = ensure_instance(graph, "scene1.start", factory, world=world)
        scene1_containers = list(graph.find_all(label="scene1"))
        assert len(scene1_containers) == 1

        instance2 = ensure_instance(graph, "scene1.start", factory, world=world)

        assert instance1 is instance2
        assert len(list(graph.find_all(label="scene1"))) == 1

    def test_ensure_instance_rejects_subgraph_for_non_container(self) -> None:
        """Error when a container exists but the template expects a node."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        parent = ensure_namespace(graph, "scene1.start")
        existing = Subgraph(label="start", graph=graph)
        assert parent is not None
        parent.add_member(existing)

        template = Template(
            label="start",
            obj_cls=Block,
            declares_instance=True,
        )
        factory.add(template)

        world = create_minimal_world()

        with pytest.raises(TypeError, match="Subgraph already exists but template expects Block"):
            ensure_instance(graph, "scene1.start", factory, world=world)

    def test_ensure_instance_reuses_subgraph_for_container_type(self) -> None:
        """Reuse existing subgraphs when templates expect containers."""

        graph = Graph(label="test")
        factory = TemplateFactory(label="test")

        existing = graph.add_subgraph(label="chapter1")

        template = Template(
            label="chapter1",
            obj_cls=Subgraph,
            declares_instance=True,
        )
        factory.add(template)

        world = create_minimal_world()

        result = ensure_instance(graph, "chapter1", factory, world=world)

        assert result is existing

    def test_ensure_instance_without_world_uses_class_obj_cls(self) -> None:
        """Ensure class-based templates materialize without a world."""
        factory = TemplateFactory(label="test")
        factory.add(
            HierarchicalTemplate(
                label="start",
                obj_cls=Node,
                path_pattern="*",
                declares_instance=True,
            )
        )

        graph = Graph(label="test")

        result = ensure_instance(
            graph,
            "scene1.start",
            factory,
        )

        assert isinstance(result, Node)
        assert result.label == "start"

    def test_ensure_instance_handles_string_obj_cls(self) -> None:
        """Ensure string obj_cls values are resolved before materialization."""
        factory = TemplateFactory(label="test")
        factory.add(
            HierarchicalTemplate(
                label="start",
                obj_cls="tangl.core.graph.node.Node",
                path_pattern="*",
                declares_instance=True,
            )
        )

        graph = Graph(label="test")

        result = ensure_instance(
            graph,
            "scene1.start",
            factory,
        )

        assert isinstance(result, Node)
        assert result.label == "start"
