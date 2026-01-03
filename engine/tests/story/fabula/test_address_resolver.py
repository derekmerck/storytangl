"""Tests for address-driven resolution helpers.

Organized by functionality:
- Template resolution by scope pattern.
- Namespace prefix creation.
- Address-based instance materialization.
"""

from __future__ import annotations

import pytest
from typing import Any

from tangl.core.factory import HierarchicalTemplate, TemplateFactory
from tangl.core.graph import Graph, Node
from tangl.ir.story_ir import StoryScript
from tangl.story.episode.block import Block
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.fabula.address_resolver import (
    ensure_instance,
    ensure_namespace,
    resolve_template_for_address,
)
from tangl.story.story_graph import StoryGraph


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture(autouse=True)
def clear_world_singleton() -> None:
    """Reset the ``World`` singleton registry between tests."""

    World.clear_instances()
    yield
    World.clear_instances()


def build_world(story_data: dict[str, Any]) -> World:
    """Helper that validates ``story_data`` and instantiates a ``World``."""

    script = StoryScript.model_validate(story_data)
    manager = ScriptManager.from_master_script(master_script=script)
    return World(
        label=story_data["label"],
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=story_data.get("metadata", {}),
    )


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


# ============================================================================
# Namespace creation
# ============================================================================

class TestEnsureNamespace:
    """Tests for namespace prefix creation."""

    def test_ensure_namespace_creates_prefix_chain(self) -> None:
        """Ensure all prefix containers are created in order."""

        graph = Graph(label="test")

        result = ensure_namespace(graph, "a.b.c")

        a = graph.find_subgraph(path="a")
        b = graph.find_subgraph(path="a.b")
        c = graph.find_subgraph(path="a.b.c")

        assert a is not None
        assert b is not None
        assert c is not None
        assert b.parent == a
        assert c.parent == b
        assert result == c


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
