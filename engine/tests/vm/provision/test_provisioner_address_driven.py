"""Tests for address-driven materialization in provisioners.

Organized by functionality:
- Declared instance paths are honored during materialization.
- Scoped templates remain unavailable outside cursor scope.
"""

from __future__ import annotations

from tangl.core.factory import HierarchicalTemplate, TemplateFactory
from tangl.core.graph import Node
from types import SimpleNamespace

from tangl.story.episode.block import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner


# ============================================================================
# Address-driven materialization
# ============================================================================

class TestProvisionerAddressDriven:
    """Tests for address-driven materialization behavior."""

    def test_provisioner_uses_declared_instance_path(self) -> None:
        """Provisioner should materialize at a declared template path."""

        root = HierarchicalTemplate(
            label="scene1",
            children={
                "start": HierarchicalTemplate(
                    label="start",
                    obj_cls=Block,
                    declares_instance=True,
                )
            },
        )
        factory = TemplateFactory.from_root_templ(root)

        graph = StoryGraph(label="test", factory=factory, world=None)

        requirement = Requirement(
            graph=graph,
            template_ref="start",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )
        ctx = SimpleNamespace(graph=graph, cursor=None, cursor_id=None)

        provisioner = TemplateProvisioner(factory=factory)
        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert len(offers) == 1
        node = offers[0].accept(ctx=ctx)

        assert isinstance(node, Block)
        assert node.label == "start"
        scene = graph.find_subgraph(path="scene1")
        assert scene is not None
        assert node.parent == scene

    def test_provisioner_respects_cursor_scope(self) -> None:
        """Templates outside the cursor scope should not offer."""

        factory = TemplateFactory(label="test")
        factory.add(
            HierarchicalTemplate(
                label="guard",
                obj_cls=Node,
                path_pattern="scene2.*",
            )
        )

        graph = StoryGraph(label="test", factory=factory, world=None)
        scene1 = graph.add_subgraph(label="scene1")
        cursor = graph.add_node(label="start")
        scene1.add_member(cursor)

        requirement = Requirement(
            graph=graph,
            template_ref="guard",
            policy=ProvisioningPolicy.CREATE_TEMPLATE,
        )
        ctx = SimpleNamespace(graph=graph, cursor=cursor, cursor_id=cursor.uid)

        provisioner = TemplateProvisioner(factory=factory)
        offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))

        assert offers == []
