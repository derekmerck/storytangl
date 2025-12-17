from __future__ import annotations

import inspect

from tangl.core.graph import Graph
from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import AssetManager, DomainManager, ScriptManager, World


def test_get_scope_chain_simplified() -> None:
    """Scope chain should use cumulative qualified paths only."""

    script = StoryScript.model_validate(
        {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {},
        }
    )
    manager = ScriptManager(master_script=script)

    graph = Graph(label="test")
    village = graph.add_subgraph(label="village")
    store = graph.add_subgraph(label="store")
    counter = graph.add_node(label="counter")
    village.add_member(store)
    store.add_member(counter)

    chain = manager._get_scope_chain(counter)

    assert chain == ["village.store.counter", "village.store", "village", ""]
    assert "store.counter" not in chain
    assert "store" not in chain


def test_find_templates_plural_global_search() -> None:
    """Plural lookup should perform a global registry search."""

    World.clear_instances()

    script_data = {
        "label": "test",
        "metadata": {"title": "Test", "author": "Tests"},
        "templates": {
            "guard": {
                "obj_cls": "Node",
                "label": "guard",
                "location": "global",
                "archetype": "guard",
            },
            "village.guard": {
                "obj_cls": "Node",
                "label": "village.guard",
                "location": "village",
                "archetype": "guard",
            },
            "city.guard": {
                "obj_cls": "Node",
                "label": "city.guard",
                "location": "city",
                "archetype": "guard",
            },
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(script_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="test",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    try:
        results = world.script_manager.find_templates(archetype="guard")

        assert len(results) == 3
    finally:
        World.clear_instances()


def test_provisioner_avoids_dict_access() -> None:
    """Provisioner should not reach into ``world.__dict__``."""

    from tangl.vm.provision.provisioner import TemplateProvisioner

    source = inspect.getsource(TemplateProvisioner)

    assert "__dict__" not in source
    assert "getattr(world, \"script_manager\"" in source or "getattr(world, 'script_manager'" in source


def test_find_template_singular_prefers_scope_chain() -> None:
    """Singular lookup should return the first match from scope chain."""

    World.clear_instances()

    script_data = {
        "label": "test",
        "metadata": {"title": "Test", "author": "Tests"},
        "templates": {
            "guard": {"obj_cls": "Node", "label": "guard", "priority": 3},
            "village.guard": {
                "obj_cls": "Node",
                "label": "guard",
                "priority": 2,
                "scope": {"parent_label": "village"},
            },
            "village.store.guard": {
                "obj_cls": "Node",
                "label": "guard",
                "priority": 1,
                "scope": {"parent_label": "store"},
            },
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(script_data)
    manager = ScriptManager(master_script=script)
    world = World(
        label="test",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata={},
    )

    try:
        from tangl.story.story_graph import StoryGraph

        graph = StoryGraph(label="test", world=world)
        village = graph.add_subgraph(label="village")
        store = graph.add_subgraph(label="store")
        counter = graph.add_node(label="counter")
        village.add_member(store)
        store.add_member(counter)

        result = world.script_manager.find_template(identifier="guard", selector=counter)
        assert result is not None
        assert getattr(result.scope, "parent_label", None) == "store"

        village_result = world.script_manager.find_template(identifier="guard", selector=village)
        assert village_result is not None
        assert getattr(village_result.scope, "parent_label", None) == "village"
    finally:
        World.clear_instances()
