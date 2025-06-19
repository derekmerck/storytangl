import pytest
from uuid import UUID, uuid4
import pickle

from pydantic import Field

from tangl.core.entity import Entity

def test_has_alias():
    e = Entity(label="hero")
    assert e.has_alias("hero")
    assert not e.has_alias("villain")

def test_get_identifiers():
    e = Entity(label="hero")
    assert e.has_identifier("hero")
    assert e.has_identifier(e.uid)

def test_has_aliases():
    class MyEntity(Entity):
        alias: set = Field(..., json_schema_extra={'is_identifier': True})

    e = MyEntity(alias={'alias1', 'alias2'}, label='test_entity')
    assert e.has_alias('alias1')
    assert e.has_alias('alias2')
    assert not e.has_alias('alias3')

    assert e.has_alias(e.label)
    assert e.has_alias(e.short_uid)


def test_filtering():
    class MyEntity(Entity):
        alias: set = Field(..., json_schema_extra={'is_identifier': True})

    e0 = MyEntity(alias={'alias1'})
    e1 = MyEntity(alias={'alias1'}, tags={'tag1'})
    e2 = MyEntity(alias={'alias2'}, tags={'tag2'})
    e3 = MyEntity(alias=set(), tags={'tag1', 'tag3', 'tag4'})

    instances = [e0, e1, e2, e3]
    filtered = Entity.filter_by_criteria(instances, alias='alias1')
    assert list(filtered) == [e0, e1], "e0 and e1 both use that alias"
    filtered = Entity.filter_by_criteria(instances, alias='alias1', tags=None)
    assert list(filtered) == [e0], "None query should fail on e1"

    filtered = Entity.filter_by_criteria(instances, tags={'tag2'})
    assert list(filtered) == [e2]
    # checking alias = None doesn't make any sense, just leave it blank
    # filtered = Entity.filter_by_criteria(instances, alias=None, tags={'tag2'})
    # assert filtered == [e2]

    filtered = Entity.filter_by_criteria(instances, tags={'tag1', 'tag2'})
    assert list(filtered) == []

    filtered = Entity.filter_by_criteria(instances, tags={'tag1', 'tag3'})
    assert list(filtered) == [e3]

