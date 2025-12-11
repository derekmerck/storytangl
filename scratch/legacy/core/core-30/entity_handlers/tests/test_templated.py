from __future__ import annotations
from typing import ClassVar
import logging

import pytest
from pydantic import Field, SkipValidation

from tangl.core.entity import Entity
from tangl.core.entity.handlers import SelfFactoringModel
from tangl.core.entity.handlers import HasTemplates, TemplateHandler

logging.basicConfig(level=logging.DEBUG)


class TestTemplatedEntity(HasTemplates, Entity, metaclass=SelfFactoringModel):

    class_template_map: ClassVar[dict] = {'dog': {'foo': 'puppy',
                                                  'good': 'dog'},
                                         'pig': {'foo': 'piglet'},
                                         'labradoodle': {'template_names': ['dog'],
                                                         'hello': 'goodbye',
                                                         'good':  'girl'}
                          }
    foo: str
    hello: str = "hello"
    good: str = "boy"
    reduce_me: SkipValidation[str] = Field("red", json_schema_extra={'reduce': True})

# @pytest.mark.xfail(reason="changed processing order")
def test_template_processing_order():
    # default
    foo = TestTemplatedEntity(foo="bar")
    logging.debug(foo)
    assert foo.foo == "bar"
    assert foo.hello == "hello"
    assert foo.good == "boy"
    assert foo.reduce_me == "red"

    # single template
    foo = TestTemplatedEntity(template_names=["dog"])
    assert foo.foo == "puppy"
    assert foo.good == "dog"

    # template with attrib, attrib has priority
    foo = TestTemplatedEntity(template_names=["dog"], foo="bar")
    assert foo.foo == "bar"
    assert foo.good == "dog"

    # multiple templates, first has priority
    foo = TestTemplatedEntity(template_names=["dog", "pig"])
    assert foo.foo == "puppy"
    assert foo.good == "dog"

    # inverse order templates, first has priority
    foo = TestTemplatedEntity(template_names=["pig", "dog"])
    assert foo.foo == "piglet"
    assert foo.good == "dog"

    # recursive templates,
    foo = TestTemplatedEntity(template_names=["labradoodle"])
    assert foo.foo == "puppy"
    assert foo.hello == "goodbye"
    assert foo.good == "girl"

    foo = TestTemplatedEntity(template_names=["labradoodle", "dog", "labradoodle", "dog"])
    assert foo.foo == "puppy"
    assert foo.hello == "goodbye"
    assert foo.good == "girl"


def test_basic_template_processing():
    data = {}
    template_names = ['basic_template']
    template_map = {'basic_template': {'field': 'value'}}
    processed_data = TemplateHandler.process_templates(data=data,
                                                       template_names=template_names,
                                                       template_maps=[template_map])
    assert processed_data['field'] == 'value'


def test_template_inheritance():
    data = {'template_names': ['child']}
    template_map = {
        'parent': {'field': 'parent_value', 'common_field': 'parent_common_value'},
        'child': {'template_names': ['parent'], 'field': 'child_value'}
    }
    processed_data = TemplateHandler.process_templates(data, template_maps=[template_map])
    assert processed_data['field'] == 'child_value'
    assert processed_data['common_field'] == 'parent_common_value'

def test_disallowed_keys():
    data = {'template_names': ['invalid_template']}
    template_map = {'invalid_template': {'uid': '12345'}}
    with pytest.raises(ValueError):
        TemplateHandler.process_templates(data, template_maps=[template_map])

# @pytest.mark.xfail(reason="default reduce not working with templates")
def test_default_reduction():

    values = ["dog", "cat", "mouse"]
    data = {'reduce_me': values}
    node = TestTemplatedEntity(foo="foo", **data)
    # processed_data = TemplateHandler.reduce_defaults(node)
    assert node.reduce_me in values  # Expected pick

    value = {'dog': 10, 'cat': 20}
    data = {'reduce_me': value}
    node = TestTemplatedEntity(foo="foo", **data)
    # processed_data = TemplateHandler.reduce_defaults(node)
    assert node.reduce_me in value.keys()  # Expected weighted pick

    value = [0, 100]
    data = {'reduce_me': value}
    node = TestTemplatedEntity(foo="foo", **data)
    # processed_data = TemplateHandler.reduce_defaults(node)
    assert 0 <= node.reduce_me <= 100  # Expected numeric in range


TEMPLATE_MAPS = [
    # tests basic features
    {'basic':    {'color': 'blue', 'size': 'M'},
     'advanced': {'color': 'red', 'material': 'cotton'},
     'derived':  {'template_names': ['basic'], 'size': 'large'},
     'invalid':  {'obj_cls': 'SomeClass'},
     'recursive': {'template_names': ['recursive']}
     },
    # tests that multiple template maps can be applied
    {'basic':    {'color': 'blue', 'size': 'M'},
     'extended': {'template_names': ['basic'], 'material': 'cotton'},
     'special':  {'template_names': ['extended'], 'color': 'red'},
     },
    # tests that multiple template maps give precedence to _later_ templates
    {'advanced': {'color': 'purple'},
     },
]

class TestTemplatedEntity2(HasTemplates, Entity, metaclass=SelfFactoringModel):
    class_template_map = TEMPLATE_MAPS[0]
    color: str = None
    size: str = None
    material: str = None

def test_single_template_injection():

    data = {'template_names': ['basic']}
    e = TestTemplatedEntity2(**data)
    assert e.color == 'blue'
    assert e.size == 'M'

@pytest.mark.xfail(reason="changed processing order")
def test_extra_template_maps_injection():

    template_maps = [{'basic': {'color': 'green', 'material': 'plastic'}}]
    data = {'template_names': ['basic'], 'template_maps': template_maps}
    e = TestTemplatedEntity2(**data)
    assert e.color == 'green'  # 'template_maps' overrides default extra maps
    assert e.size == 'M'
    assert e.material == 'plastic'

def test_multiple_template_injection_and_override():

    data = {'template_names': ['advanced', 'basic']}
    e = TestTemplatedEntity2(**data)
    assert e.color == 'red'  # "advanced' has priority
    assert e.size == 'M'
    assert e.material == 'cotton'

    data = {'template_names': ['basic', 'advanced']}
    e = TestTemplatedEntity2(**data)
    assert e.color == 'blue'  # 'basic' has priority
    assert e.size == 'M'
    assert e.material == 'cotton'

def test_recursive_template_processing():

    data = {'template_names': ['special'], 'template_maps': [ TEMPLATE_MAPS[1] ]}
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
