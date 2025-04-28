import logging

logger = logging.getLogger(__name__)

import pytest

from tangl.core.entity_handlers import on_gather_context, HasContext
from tangl.core.graph import Graph, Node
from tangl.core.graph_handlers import HasScopedContext

MyContextNode = type('MyContextNode', (HasScopedContext, Node), {} )
MyContextGraph = type('MyContextGraph', (HasContext, Graph), {} )

@pytest.fixture
def context_node():
    g = MyContextGraph(locals={'graph': 'hello graph'})
    n = MyContextNode(locals={'node': 'hello node'})
    g.add(n)
    yield n

@pytest.fixture
def context_node_child(context_node):
    c = MyContextNode(locals={'child': 'hello child'})
    context_node.add_child(c)
    yield c

def test_context_graph(context_node):

    result = on_gather_context.execute(context_node.graph)
    assert {'graph': 'hello graph'}.items() <= result.items()

def test_context_node(context_node):

    result = on_gather_context.execute(context_node)
    assert {"node": "hello node", 'graph': 'hello graph'}.items() <= result.items()

def test_context_node_child(context_node_child):

    result = on_gather_context.execute(context_node_child)
    assert {"node": "hello node", "child": "hello child", 'graph': 'hello graph'}.items() <= result.items()

def test_namespace_inheritance1():
    graph = Graph()
    parent = MyContextNode(locals={'parent_var': 'parent'})
    graph.add(parent)
    child = MyContextNode(locals={'child_var': 'child'})
    parent.add_child(child)

    child_ns = child.gather_context()
    assert child_ns['child_var'] == 'child'
    assert child_ns['parent_var'] == 'parent'

def test_namespace_inheritance2():
    # Create instances of Parent and Child
    parent = MyContextNode()
    child = MyContextNode()
    parent.add_child(child)

    print( child.gather_context() )
    # Set a local variable in the parent
    parent.locals['var1'] = 'value1'

    print( child.gather_context() )

    # Check that the child can access the parent's local variable
    assert child.gather_context()['var1'] == 'value1'

    # Set a local variable in the child
    child.locals['var2'] = 'value2'

    # Check that the child's local variable is accessible
    assert child.gather_context()['var2'] == 'value2'

    # Check that the parent's local variable is still accessible
    assert child.gather_context()['var1'] == 'value1'

    # Check that the parent cannot access the child's local variable
    with pytest.raises(KeyError):
        parent.gather_context()['var2']

def test_ancestor_namespace_inherits():
    graph = Graph()
    root = MyContextNode(locals={'root_var': 'root'})
    graph.add(root)
    mid = MyContextNode(locals={'mid_var': 'mid'})
    root.add_child(mid)
    leaf = MyContextNode(locals={'leaf_var': 'leaf'})
    mid.add_child(leaf)

    leaf_ns = leaf.gather_context()
    assert leaf_ns['root_var'] == 'root'
    assert leaf_ns['mid_var'] == 'mid'
    assert leaf_ns['leaf_var'] == 'leaf'

def test_graph_namespace_inherits():
    index = MyContextGraph(locals={'variable': 'value'})
    node = MyContextNode(label='test_node', graph=index)

    assert 'variable' in index.gather_context()
    assert index.gather_context()['variable'] == 'value'

    assert 'variable' in node.gather_context()
    assert node.gather_context()['variable'] == 'value'

def test_grandparent_namespace_inherits():
    grandparent = MyContextNode(label="grandparent", locals={"x": 1, "y": 1, "z": 1})
    parent = MyContextNode(label="parent", locals={"y": 2, "z": 2})
    grandparent.add_child(parent)
    child = MyContextNode(label="child", locals={"z": 3})
    parent.add_child(child)
    namespace = child.gather_context()
    assert "x" in namespace
    assert "y" in namespace
    assert "z" in namespace
    assert namespace["x"] == 1
    assert namespace["y"] == 2
    assert namespace["z"] == 3

# class ConditionalNode(HasInheritedNamespace, Conditional, Lockable,  Node):
#     pass
#
# def test_conditional_with_inherited_namespace():
#     graph = Graph()
#     parent = ConditionalNode(locals={'parent_var': 'parent'}, conditions=["parent_var == 'parent'"])
#     graph.add_node(parent)
#     child = ConditionalNode(conditions=["parent_var == 'parent'"])
#     parent.add_child(child)
#     assert child.check()

# Conditions do not cascade like availability
# @pytest.mark.xfail(reason="conditions on grandparents don't use grandchild's namespace?")
# def test_nested_conditions():
#     parent = MockNode(uid="parent", conditions=["x > 0"])
#     child = MockNode(uid="child", parent=parent, conditions=["y == 'foo'"])
#     grandchild = MockNode(uid="grandchild", parent=child, conditions=["z < 5"])
#
#     grandchild.local_namespace = {"x": 1, "y": "foo", "z": 4}
#     assert grandchild.available
#
#     grandchild.local_namespace["x"] = 0
#     assert not grandchild.available

from tangl.core import HasEffects, HasConditions, Renderable

MyApplyableNode = type('MyApplyableNode', (HasEffects, HasScopedContext, Node), {} )

def test_effect_with_inherited_namespace():
    graph = Graph()
    parent = MyApplyableNode(locals={'parent_var': {}})
    graph.add(parent)
    child = MyApplyableNode(effects=["parent_var['foo'] = 'bar'"])
    parent.add_child(child)
    child.apply_effects()
    assert parent.locals['parent_var']['foo'] == 'bar'

MyRenderableNode = type('MyRenderableNode', (Renderable, HasScopedContext, Node), {} )

def test_rendering_with_inherited_namespace():
    graph = Graph()
    parent = MyRenderableNode(locals={'parent_var': 'parent'})
    graph.add(parent)
    child = MyRenderableNode(content='pv: {{parent_var}}')
    parent.add_child(child)
    output = child.render()
    assert output['content'] == 'pv: parent'

MyConditionsNode = type('MyConditionsNode', (HasConditions, HasScopedContext, Node), {} )

def test_conditional_with_inherited_namespace():
    graph = Graph()
    parent = MyConditionsNode(locals={'parent_var': 'parent'}, conditions=["parent_var == 'parent'"], graph=graph)
    logger.debug(parent.gather_context())
    logger.debug(parent.conditions)
    assert parent.check_conditions()

    child = MyConditionsNode(conditions=["parent_var == 'parent'"], graph=graph)
    parent.add_child(child)
    logger.debug(child.gather_context())
    logger.debug(child.conditions)
    assert child.check_conditions()
