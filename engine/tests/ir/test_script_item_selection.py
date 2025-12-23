from tangl.ir.core_ir.base_script_model import BaseScriptItem
# from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_global_template_selection_criteria_empty():
    template = BaseScriptItem(label="global")

    assert template.get_selection_criteria() == {}


def test_scene_template_selection_criteria_parent_label():
    template = BaseScriptItem(label="scene-template", scope_path="scene1.*")

    assert template.get_selection_criteria() == {"has_path": "scene1.*"}


# def test_block_template_selection_criteria_source_label():
#     template = BaseScriptItem(label="block-template", scope=ScopeSelector(source_label="block1"))
#
#     assert template.get_selection_criteria() == {"label": "block1"}


def test_complex_template_selection_criteria():
    scope = ScopeSelector(
        parent_label="scene1",
        ancestor_labels={"world*"},
        ancestor_tags={"tag1", "tag2"},
        source_label="block1",
    )
    template = BaseScriptItem(label="complex", scope_path="world.scene1.block1", scope_tags={'tag1', 'tag2'})

    assert template.get_selection_criteria() == {
        "has_path": "world.scene1.block1",
        "has_ancestor_tags": {"tag1", "tag2"},
    }
