from tangl.core.graph import Graph
from tangl.core.graph.scope_selectable import ScopeSelectable


def test_scope_rank_without_selector():
    """Verify scope_rank works without selector context."""
    template1 = ScopeSelectable(label="guard", path_pattern="*")
    template2 = ScopeSelectable(label="guard", path_pattern="village.*")
    template3 = ScopeSelectable(label="guard", path_pattern="village.tavern.*")

    templates = [template1, template2, template3]
    sorted_templates = sorted(templates, key=lambda template: template.scope_rank())

    assert sorted_templates[0] == template3
    assert sorted_templates[1] == template2
    assert sorted_templates[2] == template1


def test_scope_rank_with_selector():
    """Verify scope_rank uses selector context when available."""
    graph = Graph()
    village = graph.add_subgraph(label="village")
    tavern = graph.add_subgraph(label="tavern")
    bar = graph.add_node(label="bar")

    village.add_member(tavern)
    tavern.add_member(bar)

    global_guard = ScopeSelectable(label="guard", path_pattern="*")
    village_guard = ScopeSelectable(label="guard", path_pattern="village.*")
    tavern_guard = ScopeSelectable(label="guard", path_pattern="village.tavern.*")

    templates = [global_guard, village_guard, tavern_guard]
    sorted_templates = sorted(templates, key=lambda template: template.scope_rank(bar))

    assert sorted_templates[0] == tavern_guard
