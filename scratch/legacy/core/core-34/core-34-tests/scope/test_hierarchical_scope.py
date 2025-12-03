import pytest
from tangl.core.scope.hierarchical_scope import HierarchicalScope
from tangl.core.entity import Graph


@pytest.fixture
def simple_graph():
    graph = Graph()
    root = HierarchicalScope(label="root", graph=graph)

    child1 = HierarchicalScope(label="child1", graph=graph, parent=root)
    child2 = HierarchicalScope(label="child2", graph=graph, parent=root)
    root.add_child(child1)
    root.add_child(child2)

    grandchild = HierarchicalScope(label="grandchild", graph=graph, parent=child1)
    child1.add_child(grandchild)

    return graph, root, child1, child2, grandchild


def test_hierarchy_structure(simple_graph):
    graph, root, child1, child2, grandchild = simple_graph

    assert child1.parent == root
    assert child2.parent == root
    assert grandchild.parent == child1

    assert set([c.uid for c in root.children]) == {child1.uid, child2.uid}
    assert list(child1.children) == [grandchild]
    assert list(child2.children) == []


def test_hierarchy_ancestors(simple_graph):
    _, root, child1, _, grandchild = simple_graph

    assert list(grandchild.ancestors) == [grandchild, child1, root]
    assert list(child1.ancestors) == [child1, root]
    assert list(root.ancestors) == [root]


def test_hierarchy_paths(simple_graph):
    _, root, child1, _, grandchild = simple_graph

    assert root.path == "root"
    assert child1.path == "root/child1"
    assert grandchild.path == "root/child1/grandchild"


def test_context_inheritance(simple_graph):
    _, root, child1, _, grandchild = simple_graph

    root.locals = {"location": "castle"}
    child1.locals = {"npc": "guard"}
    grandchild.locals = {"item": "sword"}

    grandchild_ctx = grandchild.gather_context()
    print(grandchild_ctx)
    assert grandchild_ctx["location"] == "castle"
    assert grandchild_ctx["npc"] == "guard"
    assert grandchild_ctx["item"] == "sword"

    child1_ctx = child1.gather_context()
    assert child1_ctx["location"] == "castle"
    assert child1_ctx["npc"] == "guard"
    assert "item" not in child1_ctx


def test_add_remove_child(simple_graph):
    graph, root, child1, child2, _ = simple_graph

    # Remove child2
    root.remove_child(child2)
    assert list(root.children) == [child1]

    # Add back child2
    root.add_child(child2)
    assert set([c.uid for c in root.children]) == {child1.uid, child2.uid}


def test_remove_child_with_discard(simple_graph):
    graph, root, child1, _, grandchild = simple_graph

    # Remove grandchild with discard
    child1.remove_child(grandchild, discard=True)
    assert grandchild.uid not in graph
    assert list(child1.children) == []