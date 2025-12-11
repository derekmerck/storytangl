from __future__ import annotations

import pytest

from tangl.graph import Node
from tangl.graph import HierarchicalStructuringHandler

class TestChildFieldNode(Node):
    name: str = None

    @property
    def node_list(self) -> list[TestChildFieldNode]:
        return self.find_children(TestChildFieldNode)

    @property
    def node_dict(self) -> list[TestChildFieldNode]:
        return self.find_children(TestChildFieldNode)

    @property
    def sp_node(self) -> TestCFSubclassNode:
        return self.find_child(TestCFSubclassNode)

class TestCFSubclassNode(TestChildFieldNode):
    ...

@pytest.fixture
def data():
    return {
        'obj_cls': TestChildFieldNode,
        'name': 'parent',
        'node_list': [
            {'name': 'first_child'},
            {'name': 'second_child',
             'node_list': [{'name': 'grandchild'}]
             },
        ],
        'node_dict': {
            'dog': {'name': 'rex'},
            'cat': {'name': 'princess',
                    'node_dict': {'bird': {'obj_cls': 'TestCFSubclassNode'} }
                    }
        },
    }

def test_hierarchical_structuring(data):

    parent = HierarchicalStructuringHandler.structure_node(**data)
    print( parent )

    assert parent.node_list[0].name in ["first_child", "second_child", "rex", "princess"]
    assert isinstance(parent.node_list[0], TestChildFieldNode)

    second_child = parent.find_child(filt=lambda x: x.name == "second_child")
    assert second_child.node_list[0].name == "grandchild"
    assert isinstance(second_child, TestChildFieldNode)

    princess = parent.find_child(filt=lambda x: x.label == "cat")
    assert princess.node_dict[0].label == "bird"
    assert isinstance(princess, TestChildFieldNode)
    assert princess.node_list[0].__class__ is TestCFSubclassNode

from tangl.entity.mixins import Templated

class TestTemplatedChildFieldNode(Templated, TestChildFieldNode):
    my_obj: TestTemplatedChildFieldNode = None

class TestTemplatedCFSubclassNode(TestTemplatedChildFieldNode):

    class_template_map = {'a': {'name': 'name_a'}}


@pytest.fixture
def data_templ():
    return {
        'obj_cls': TestTemplatedChildFieldNode,
        'label': 'parent',
        'templates': ['a', 'b', 'c'],
        'name': 'parent',
        'node_list': [
            {'name': 'first_child'},
            {'name': 'second_child',
             'node_list': [{'name': 'grandchild'}]
             },
        ],
        'node_dict': {
            'dog': {'name': 'rex'},
            'cat': {'name': 'princess',
                    'node_dict': {'bird': {
                        'obj_cls': 'TestTemplatedCFSubclassNode',
                        'templates': ['a', 'b', 'c']} }
                    }
        },
        'sp_node': {'label': 'sp_node', 'obj_cls': 'TestCFSubclassNode', 'templates': ['b']},
        # 'my_obj': {'obj_cls': 'TestTemplatedChildNode'}

    }

def test_hierarchical_w_template_cls(data_templ):

    parent = HierarchicalStructuringHandler.structure_node(**data_templ)
    print( parent )

    cat = parent.get_child("cat")
    assert isinstance(cat, TestChildFieldNode)

    bird = cat.get_child("bird")
    assert isinstance(bird, TestTemplatedCFSubclassNode)
    assert bird.name == "name_a"

    sp_node = parent.get_child("sp_node")
    assert isinstance(sp_node, Node)
