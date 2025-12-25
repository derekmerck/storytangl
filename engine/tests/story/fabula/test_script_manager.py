import logging

import pytest

from tangl.story.concepts.actor import Actor
from tangl.story.episode import Scene
from tangl.story.fabula.script_manager import ScriptManager

logger = logging.getLogger(__name__)

script_data = {
    "label": "hierarchical",
    "metadata": {"title": "Hierarchy Test", "author": "Tests"},
    "actors": {
        "guard": {
            "label": "~guard",
            "name": "Generic Guard",
        },
        "village.guard": {
            "label": "guard",
            "path_pattern": "~village.*",
            "name": "Village Guard",
        },
        "village.store.guard": {
            "label": "guard",
            "path_pattern": "~village.store.*",
            "name": "Store Guard",
        },
        "countryside.guard": {
            "label": "guard",
            "path_pattern": "~countryside.*",
            "name": "Countryside Guard",
        },
    },
    "scenes": {
        "opening scene": {
            "blocks": {
                "start block": {}
            }
        }
    },
}

@pytest.fixture(scope="module")
def script_manager():
    return ScriptManager.from_data(script_data)

def test_master_script_(script_manager):

    all_paths = script_manager.template_factory.all_paths()
    logger.debug(f"all paths: {all_paths}")
    assert len(all_paths) > 3

    all_values = list(script_manager.template_factory.values())
    logger.debug(f"all values: {all_values}")
    assert len(all_paths) > 3

    find_all = list(script_manager.template_factory.find_all())
    logger.debug(f"find_all: {find_all}")
    assert len(find_all) > 3

    find_templs = list(script_manager.find_templates())
    logger.debug(f"find_templates: {find_templs}")
    assert len(find_templs) > 3

    find_actors = list(script_manager.find_actors())
    logger.debug(f"find_actors: {find_actors}")
    assert len(find_actors) > 3

    logger.debug(f"find_actors: {[(a.name, a.get_path_pattern(), a.scope_specificity()) for a in find_actors]}")

    assert find_actors[0].name == "Store Guard"
    assert find_actors[-1].name == "Generic Guard"

    scene_templ = next( script_manager.find_scenes(identifier="opening scene") )
    logger.debug(f"scene: {scene_templ}")
    sc = scene_templ.materialize()
    assert isinstance(sc, Scene)
    logger.debug(f"scene: {sc}")
    assert sc.get_label() == "opening_scene"  # note underscore

def test_materialize_actors(script_manager):

    for item in script_manager.find_actors():
        actor = item.materialize()
        assert isinstance(actor, Actor)
        logger.debug(f"actor: {actor}")


