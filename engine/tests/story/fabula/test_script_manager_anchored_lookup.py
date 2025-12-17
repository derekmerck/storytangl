from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tangl.core.graph import Graph, Node
from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World
from tangl.story.story_graph import StoryGraph
from tangl.vm.context import Context
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner


@pytest.fixture
def hierarchical_world():
    """World with nested scopes for anchored template lookup."""

    World.clear_instances()

    script_data = {
        "label": "hierarchical",
        "metadata": {"title": "Hierarchy Test", "author": "Tests"},
        "templates": {
            "guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "label": "guard",
                "name": "Generic Guard",
            },
            "village.guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "label": "guard",
                "scope": {"parent_label": "village"},
                "name": "Village Guard",
            },
            "village.store.guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "label": "guard",
                "scope": {"parent_label": "store"},
                "name": "Store Guard",
            },
            "countryside.guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "label": "guard",
                "scope": {"parent_label": "countryside"},
                "name": "Countryside Guard",
            },
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(script_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="hierarchical",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    yield world
    World.clear_instances()


def test_is_qualified_identifier():
    """ScriptManager should flag identifiers containing scope separators."""

    script = StoryScript.model_validate(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {},
        }
    )
    manager = ScriptManager(master_script=script)

    assert not manager._is_qualified("guard")
    assert manager._is_qualified("village.guard")
    assert manager._is_qualified("a.b")


def test_get_scope_chain_from_nested_node():
    """Anchored scope chain should progress from node to global."""

    graph = Graph(label="test")
    village = graph.add_subgraph(label="village")
    store = graph.add_subgraph(label="store")
    counter = graph.add_node(label="counter")
    village.add_member(store)
    store.add_member(counter)

    script = StoryScript.model_validate(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {},
        }
    )
    manager = ScriptManager(master_script=script)

    assert manager._get_scope_chain(counter) == [
        "village.store.counter",
        "village.store",
        "counter",
        "store",
        "village",
        "",
    ]


def test_unqualified_identifier_searches_scope_chain(hierarchical_world):
    """Unqualified identifiers should resolve from the deepest scope upward."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")
    store = graph.add_subgraph(label="store")
    counter = graph.add_node(label="counter")
    village.add_member(store)
    store.add_member(counter)

    result = hierarchical_world.script_manager.find_template(
        identifier="guard",
        selector=counter,
    )

    assert result is not None
    assert result.name == "Store Guard"


def test_unqualified_identifier_falls_back_to_parent_scope(hierarchical_world):
    """Anchored lookup should continue up to ancestors when missing locally."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")
    tavern = graph.add_subgraph(label="tavern")
    village.add_member(tavern)

    result = hierarchical_world.script_manager.find_template(
        identifier="guard",
        selector=tavern,
    )

    assert result is not None
    assert result.has_identifier("village.guard")
    assert result.name == "Village Guard"


def test_unqualified_identifier_falls_back_to_global(hierarchical_world):
    """If no ancestors contain the identifier, global templates should answer."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    mountains = graph.add_subgraph(label="mountains")
    peak = graph.add_node(label="peak")
    mountains.add_member(peak)

    result = hierarchical_world.script_manager.find_template(
        identifier="guard",
        selector=peak,
    )

    assert result is not None
    assert result.has_identifier("guard")
    assert result.name == "Generic Guard"


def test_unqualified_identifier_never_searches_sibling_scopes(hierarchical_world):
    """Anchored lookup must not jump across branches."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")
    tavern = graph.add_node(label="tavern")
    village.add_member(tavern)

    result = hierarchical_world.script_manager.find_template(
        identifier="guard",
        selector=tavern,
    )

    assert result is not None
    assert result.has_identifier("village.guard")
    assert result.name == "Village Guard"


def test_qualified_identifier_bypasses_scope_filtering(hierarchical_world):
    """Qualified identifiers should return exact matches regardless of scope."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")

    result = hierarchical_world.script_manager.find_template(
        identifier="countryside.guard",
        selector=village,
    )

    assert result is not None
    assert result.has_identifier("countryside.guard")
    assert result.name == "Countryside Guard"


def test_qualified_identifier_exact_match_only(hierarchical_world):
    """Qualified lookups should not return partial matches."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")

    result = hierarchical_world.script_manager.find_template(
        identifier="village.bakery.guard",
        selector=village,
    )

    assert result is None


def test_unqualified_without_selector_uses_global_only(hierarchical_world):
    """Without selector context, unqualified names fall back to global search."""

    result = hierarchical_world.script_manager.find_template(identifier="guard")

    assert result is not None
    assert result.label == "guard"
    assert result.name == "Generic Guard"


def test_find_template_with_additional_criteria(hierarchical_world):
    """Anchored lookup should respect additional filtering criteria."""

    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")

    result = hierarchical_world.script_manager.find_template(
        identifier="guard",
        selector=village,
        name="Village Guard",
    )

    assert result is not None
    assert result.has_identifier("village.guard")


def test_find_templates_plural_returns_all_in_scope():
    """Plural lookup should return all templates matching criteria."""

    World.clear_instances()

    script_data = {
        "label": "multi",
        "metadata": {"title": "Multi", "author": "Tests"},
        "templates": {
            "guard1": {
                "obj_cls": "tangl.core.graph.Node",
                "label": "guard1",
                "archetype": "guard",
            },
            "guard2": {
                "obj_cls": "tangl.core.graph.Node",
                "label": "guard2",
                "archetype": "guard",
            },
            "merchant": {
                "obj_cls": "tangl.core.graph.Node",
                "label": "merchant",
                "archetype": "trader",
            },
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(script_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="multi",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    try:
        results = world.script_manager.find_templates(archetype="guard")
        labels = {r.label for r in results}

        assert labels == {"guard1", "guard2"}
    finally:
        World.clear_instances()


def test_provisioning_uses_anchored_lookup(hierarchical_world):
    graph = StoryGraph(label="test", world=hierarchical_world)
    village = graph.add_subgraph(label="village")
    store = graph.add_subgraph(label="store")
    counter = graph.add_node(label="counter")
    village.add_member(store)
    store.add_member(counter)

    provisioned_labels: list[str] = []

    def _materialize(template, graph, parent_container=None):  # noqa: ANN001
        node = Node(label=template.label, graph=graph)
        provisioned_labels.append(template.name)
        if parent_container is not None:
            parent_container.add_member(node)
        return node

    hierarchical_world._materialize_from_template = Mock(side_effect=_materialize)
    script_manager = hierarchical_world.script_manager
    script_manager.find_template = Mock(wraps=script_manager.find_template)
    hierarchical_world.script_manager = script_manager

    requirement = Requirement(
        graph=graph,
        template_ref="guard",
        policy=ProvisioningPolicy.CREATE,
    )
    provisioner = TemplateProvisioner(layer="author")
    ctx = SimpleNamespace(graph=graph, cursor=counter, cursor_id=counter.uid, step=0)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert offers

    offers[0].accept(ctx=ctx)

    selectors = [call.kwargs.get("selector") for call in script_manager.find_template.call_args_list]
    assert counter in selectors
    assert provisioned_labels[-1] == "Store Guard"
