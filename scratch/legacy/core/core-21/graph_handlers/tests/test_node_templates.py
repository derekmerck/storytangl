from pydantic import Field
from typing import ClassVar

from tangl.entity import Entity
from tangl.graph import Node, GraphFactory
from tangl.entity.mixins import Templated

class TestTemplatedNode(Templated, Node):
    class_template_map: ClassVar[dict] = {
         'basic':    {'color': 'blue', 'size': 'M'},
         'advanced': {'color': 'red', 'material': 'cotton'},
         'derived':  {'templates': ['basic'], 'size': 'large'},
         'invalid':  {'node_cls': 'SomeClass'},
         'recursive': {'templates': ['recursive']}
    }
    color: str = None
    size: str = None
    material: str = None


def test_node_template_injection():

    data = {'templates': ['basic']}
    e = TestTemplatedNode(**data, template_maps=[ {'basic': {'color': 'blue', 'size': 'M'}}])

    assert e.color == 'blue'
    assert e.size == 'M'


def test_hierarchical_factory_template_injection():

    data = {'templates': ['basic']}
    e = GraphFactory().create_node(obj_cls=TestTemplatedNode, **data, template_maps=[ {'basic': {'color': 'blue', 'size': 'M'}}])

    assert e.color == 'blue'
    assert e.size == 'M'
