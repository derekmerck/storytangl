from tangl.ir.core_ir.base_script_model import BaseScriptItem
# from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_global_template_selection_criteria_empty():
    template = BaseScriptItem(label="global")

    assert template.get_selection_criteria() == {}


def test_scene_template_selection_criteria_parent_label():
    template = BaseScriptItem(label="scene-template", path_pattern="scene1.*")

    assert template.get_selection_criteria() == {"has_path": "scene1.*"}


def test_complex_template_selection_criteria():

    template = BaseScriptItem(label="complex", path_pattern="world.scene1.block1", ancestor_tags={'tag1', 'tag2'})

    assert template.get_selection_criteria() == {
        "has_path": "world.scene1.block1",
        "has_ancestor_tags": {"tag1", "tag2"},
    }
