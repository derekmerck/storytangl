from tangl.core.graph import Graph
from tangl.ir.core_ir.base_script_model import BaseScriptItem
# from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_template_gates_on_scope_via_selector():
    template = BaseScriptItem(label="cop", ancestor_tags={"town"})

    graph = Graph()
    world = graph.add_subgraph(label="world", tags={"town"})
    block = graph.add_node(label="block")
    other_block = graph.add_node(label="other")

    assert template.get_selection_criteria()['has_ancestor_tags'] == {'town'}
    assert not template.matches(selector=block)
    world.add_member(block)
    assert template.matches(selector=block)

    assert not template.matches(selector=other_block)


def test_template_matches_still_allows_inline_criteria():
    template = BaseScriptItem(label="cop")
    graph = Graph()
    selector = graph.add_node(label="anything")

    assert template.matches(selector=selector, label="cop")
    assert not template.matches(selector=selector, label="nope")


def test_selectable_mro_uses_entity_matches():
    template = BaseScriptItem(label="gate", path_pattern="parent.*")
    graph = Graph()
    parent = graph.add_subgraph(label="parent")
    selector = graph.add_node(label="child", tags=set())

    parent.add_member(selector)

    assert template.matches(selector=selector)
    assert template.matches(label="gate")
