import pytest
from tangl.core.entity import Node, Graph
from tangl.core.handler import HasContext

class TestMixinNode(HasContext, Node):
    pass

@pytest.fixture
def setup_graph():
    graph = Graph()
    parent = TestMixinNode(graph=graph, locked=True)  # Parent node is locked
    child = TestMixinNode(graph=graph, parent_id=parent.uid)  # Child node does not specify locked status
    return graph, parent, child

@pytest.mark.xfail(reason="not sure how this should work yet")
def test_cascading_availability(setup_graph):
    _, parent, child = setup_graph
    assert not parent.available(), "Parent should be unavailable because it is locked"
    assert not child.available(), "Child should inherit availability (locked status) from the parent"

def test_cascading_namespace(setup_graph):
    _, parent, child = setup_graph
    parent.locals = {'shared_var': 'parent_value', 'parent_only_var': 'value1'}
    child.locals = {'shared_var': 'child_value', 'child_only_var': 'value2'}

    child_ns = child.gather_context()
    assert child_ns['shared_var'] == 'child_value', "Child should override shared variable"
    assert child_ns['parent_only_var'] == 'value1', "Child should inherit variable from parent"
    assert child_ns['child_only_var'] == 'value2', "Child should have its own variable"
