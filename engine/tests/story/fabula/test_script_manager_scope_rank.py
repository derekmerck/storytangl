from tangl.core.graph import Graph
from tangl.ir.story_ir import StoryScript
from tangl.story.fabula.script_manager import ScriptManager


def test_find_template_prefers_closer_scope():
    """Verify find_template prefers templates closer to selector."""
    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "templates": {
            "global_guard": {
                "obj_cls": "tangl.story.concepts.actor.Actor",
                "label": "guard",
                "path_pattern": "*",
            },
            "village_guard": {
                "obj_cls": "tangl.story.concepts.actor.Actor",
                "label": "guard",
                "path_pattern": "village.*",
            },
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "tavern": {
                        "label": "tavern",
                    },
                },
            },
        },
    }

    script = StoryScript(**script_data)
    manager = ScriptManager.from_master_script(script)

    graph = Graph()
    village = graph.add_subgraph(label="village")
    tavern = graph.add_node(label="tavern")
    village.add_member(tavern)

    template = manager.find_template(identifier="guard", selector=tavern)

    assert template is not None
    assert template.label == "guard"
    assert template.get_path_pattern() == "village.*"


def test_find_template_without_selector_still_works():
    """Verify find_template works without selector (fallback behavior)."""
    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "templates": {
            "guard": {
                "obj_cls": "tangl.story.concepts.actor.Actor",
                "label": "guard",
            },
        },
        "scenes": {},
    }

    script = StoryScript(**script_data)
    manager = ScriptManager.from_master_script(script)

    template = manager.find_template(identifier="guard")

    assert template is not None
    assert template.label == "guard"


def test_find_templates_orders_by_proximity():
    """Verify find_templates returns results ordered by scope proximity."""
    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "templates": {
            "guard1": {
                "obj_cls": "tangl.story.concepts.actor.Actor",
                "label": "guard",
                "path_pattern": "*",
            },
            "guard2": {
                "obj_cls": "tangl.story.concepts.actor.Actor",
                "label": "guard",
                "path_pattern": "village.*",
            },
            "guard3": {
                "obj_cls": "tangl.story.concepts.actor.Actor",
                "label": "guard",
                "path_pattern": "village.market.*",
            },
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "market": {"label": "market"},
                    "tavern": {"label": "tavern"},
                },
            },
        },
    }

    script = StoryScript(**script_data)
    manager = ScriptManager.from_master_script(script)

    graph = Graph()
    village = graph.add_subgraph(label="village")
    market = graph.add_subgraph(label="market")
    stall = graph.add_node(label="stall")
    village.add_member(market)
    market.add_member(stall)

    templates = manager.find_templates(identifier="guard", selector=stall)

    assert len(templates) == 3
    assert templates[0].get_path_pattern() == "village.market.*"
    assert templates[1].get_path_pattern() == "village.*"
    assert templates[2].get_path_pattern() == "*"


def test_find_scenes_basic():
    """Verify find_scenes returns scene templates."""
    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "scenes": {
            "intro": {"label": "intro", "blocks": {"start": {}}},
            "village": {"label": "village", "blocks": {"start": {}}},
        },
    }

    script = StoryScript(**script_data)
    manager = ScriptManager.from_master_script(script)

    scenes = list(manager.find_scenes())

    assert len(scenes) >= 2
    labels = {scene.label for scene in scenes}
    assert "intro" in labels
    assert "village" in labels
