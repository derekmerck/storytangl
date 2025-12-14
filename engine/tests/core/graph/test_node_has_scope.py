from tangl.core.graph import Graph
from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_has_scope_global_selector_matches():
    graph = Graph()
    node = graph.add_node(label="block")

    assert node.has_scope(ScopeSelector()) is True


def test_has_scope_parent_label_and_source_label():
    graph = Graph()
    parent = graph.add_subgraph(label="scene1")
    node = graph.add_node(label="block1")
    parent.add_member(node)

    assert node.has_scope(ScopeSelector(parent_label="scene1")) is True
    assert node.has_scope(ScopeSelector(source_label="block1")) is True
    assert node.has_scope(ScopeSelector(source_label="other")) is False
    assert node.has_scope(ScopeSelector(parent_label="scene2")) is False


def test_has_scope_ancestor_labels_and_tags():
    graph = Graph()
    world = graph.add_subgraph(label="world", tags={"world"})
    scene = graph.add_subgraph(label="scene1", tags={"scene"})
    block = graph.add_node(label="block1")

    world.add_member(scene)
    scene.add_member(block)

    assert block.has_scope(ScopeSelector(ancestor_labels={"world"})) is True
    assert block.has_scope(ScopeSelector(ancestor_labels={"missing"})) is False
    assert block.has_scope(ScopeSelector(ancestor_tags={"world"})) is True
    assert block.has_scope(ScopeSelector(ancestor_tags={"scene", "world"})) is True
    assert block.has_scope(ScopeSelector(ancestor_tags={"dungeon"})) is False


def test_has_scope_no_parent_with_scope_constraints():
    graph = Graph()
    node = graph.add_node(label="orphan")

    assert node.has_scope(ScopeSelector(parent_label="scene1")) is False
    assert node.has_scope(ScopeSelector(ancestor_labels={"world"})) is False
    assert node.has_scope(ScopeSelector(ancestor_tags={"world"})) is False


def test_has_scope_source_label_only():
    graph = Graph()
    node = graph.add_node(label="block1")

    assert node.has_scope(ScopeSelector(source_label="block1")) is True
    assert node.has_scope(ScopeSelector(source_label="block2")) is False


def test_has_scope_with_mixed_constraints():
    graph = Graph()
    world = graph.add_subgraph(label="world", tags={"world"})
    scene = graph.add_subgraph(label="scene1", tags={"scene"})
    block = graph.add_node(label="block1")

    world.add_member(scene)
    scene.add_member(block)

    scope = ScopeSelector(
        parent_label="scene1",
        ancestor_labels={"world"},
        ancestor_tags={"world", "scene"},
        source_label="block1",
    )

    assert block.has_scope(scope) is True
    assert block.has_scope(scope.model_copy(update={"source_label": "other"})) is False
    assert (
        block.has_scope(
            scope.model_copy(update={"ancestor_tags": {"world", "dungeon"}}),
        )
        is False
    )
