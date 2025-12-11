from __future__ import annotations
from typing import ClassVar
import logging

import pytest
from pydantic import Field

from tangl.entity import Entity
from tangl.entity.mixins import Templated, TemplateHandler

logging.basicConfig(level=logging.DEBUG)


class TestTemplatedEntity(Entity):

    class_template_map: ClassVar[dict] = {'dog': {'foo': 'puppy',
                                  'good': 'dog'},
                          'pig': {'foo': 'piglet'},
                          'labradoodle': {'templates': ['dog'],
                                          'hello': 'goodbye',
                                          'good':  'girl'}
                          }
    foo: str
    hello: str = "hello"
    good: str = "boy"
    reduce_me: str = Field("red", json_schema_extra={'reduce': True})

@pytest.mark.xfail(reason="changed processing order")
def test_template_processing_order():
    # default
    foo = TestTemplatedEntity(foo="bar")
    assert foo.foo == "bar"
    assert foo.hello == "hello"
    assert foo.good == "boy"

    # single template
    foo = TestTemplatedEntity(templates=["dog"])
    assert foo.foo == "puppy"
    assert foo.good == "dog"

    # template with attrib, attrib has priority
    foo = TestTemplatedEntity(templates=["dog"], foo="bar")
    assert foo.foo == "bar"
    assert foo.good == "dog"

    # multiple templates, first has priority
    foo = TestTemplatedEntity(templates=["dog", "pig"])
    assert foo.foo == "puppy"
    assert foo.good == "dog"

    # inverse order templates, first has priority
    foo = TestTemplatedEntity(templates=["pig", "dog"])
    assert foo.foo == "piglet"
    assert foo.good == "dog"

    # recursive templates,
    foo = TestTemplatedEntity(templates=["labradoodle"])
    assert foo.foo == "puppy"
    assert foo.hello == "goodbye"
    assert foo.good == "girl"

    foo = TestTemplatedEntity(templates=["labradoodle", "dog", "labradoodle", "dog"])
    assert foo.foo == "puppy"
    assert foo.hello == "goodbye"
    assert foo.good == "girl"


def test_basic_template_processing():
    data = {'templates': ['basic_template']}
    template_map = {'basic_template': {'field': 'value'}}
    processed_data = TemplateHandler.process_templates(data, template_maps=[template_map])
    assert processed_data['field'] == 'value'


def test_template_inheritance():
    data = {'templates': ['child']}
    template_map = {
        'parent': {'field': 'parent_value', 'common_field': 'parent_common_value'},
        'child': {'templates': ['parent'], 'field': 'child_value'}
    }
    processed_data = TemplateHandler.process_templates(data, template_maps=[template_map])
    assert processed_data['field'] == 'child_value'
    assert processed_data['common_field'] == 'parent_common_value'


def test_disallowed_keys():
    data = {'templates': ['invalid_template']}
    template_map = {'invalid_template': {'uid': '12345'}}
    with pytest.raises(ValueError):
        TemplateHandler.process_templates(data, template_maps=[template_map])

@pytest.mark.xfail(reason="default reduce not working with templates")
def test_default_reduction():
    entity_cls = TestTemplatedEntity

    values = ["dog", "cat", "mouse"]
    data = {'reduce_me': values}
    node = TestTemplatedEntity(**data)
    processed_data = TemplateHandler.reduce_defaults(node)
    assert node.reduce_me in values  # Expected pick

    value = {'dog': 10, 'cat': 20}
    data = {'reduce_me': value}
    node = TestTemplatedEntity(**data)
    processed_data = TemplateHandler.reduce_defaults(node)
    assert node.reduce_me in value.keys()  # Expected weighted pick

    value = [0, 100]
    data = {'reduce_me': value}
    node = TestTemplatedEntity(**data)
    processed_data = TemplateHandler.reduce_defaults(node)
    assert 0 <= processed_data['reduce_me'] <= 100  # Expected numeric in range


TEMPLATE_MAPS = [
    # tests basic features
    {'basic':    {'color': 'blue', 'size': 'M'},
     'advanced': {'color': 'red', 'material': 'cotton'},
     'derived':  {'templates': ['basic'], 'size': 'large'},
     'invalid':  {'node_cls': 'SomeClass'},
     'recursive': {'templates': ['recursive']}
     },
    # tests that multiple template maps can be applied
    {'basic':    {'color': 'blue', 'size': 'M'},
     'extended': {'templates': ['basic'], 'material': 'cotton'},
     'special':  {'templates': ['extended'], 'color': 'red'},
     },
    # tests that multiple template maps give precedence to _later_ templates
    {'advanced': {'color': 'purple'},
     },
]

class TestTemplatedEntityDefaultMap(Templated, Entity):
    class_template_map = TEMPLATE_MAPS[0]
    color: str = None
    size: str = None
    material: str = None

def test_single_template_injection():

    data = {'templates': ['basic']}
    e = TestTemplatedEntityDefaultMap(**data)
    assert e.color == 'blue'
    assert e.size == 'M'

@pytest.mark.xfail(reason="changed processing order")
def test_extra_template_maps_injection():

    template_maps = [{'basic': {'color': 'green', 'material': 'plastic'}}]
    data = {'templates': ['basic'], 'template_maps': template_maps}
    e = TestTemplatedEntityDefaultMap(**data)
    assert e.color == 'green'  # 'template_maps' overrides default extra maps
    assert e.size == 'M'
    assert e.material == 'plastic'

def test_multiple_template_injection_and_override():

    data = {'templates': ['advanced', 'basic']}
    e = TestTemplatedEntityDefaultMap(**data)
    assert e.color == 'red'  # "advanced' has priority
    assert e.size == 'M'
    assert e.material == 'cotton'

    data = {'templates': ['basic', 'advanced']}
    e = TestTemplatedEntityDefaultMap(**data)
    assert e.color == 'blue'  # 'basic' has priority
    assert e.size == 'M'
    assert e.material == 'cotton'


def test_recursive_template_processing():

    data = {'templates': ['special'], 'template_maps': [ TEMPLATE_MAPS[1] ]}
    processed = TemplateHandler.process_templates(data)
    assert processed['color'] == 'red'
    assert processed['size'] == 'M'
    assert processed['material'] == 'cotton'

def test_derived_template():
    result = TemplateHandler.aggregate_templates(['derived'], [ TEMPLATE_MAPS[0] ])
    assert result == {'color': 'blue', 'size': 'large'}


def test_derived_with_inheritance():
    result = TemplateHandler.aggregate_templates(['basic', 'derived'], [ TEMPLATE_MAPS[0] ])
    assert result == {'color': 'blue', 'size': 'large'}
