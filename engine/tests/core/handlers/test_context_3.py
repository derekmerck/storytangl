from __future__ import annotations
import logging

from tangl.core.entity import Entity
from tangl.core.services import on_gather_context, HasContext

logging.basicConfig(level=logging.DEBUG)

class MyEntity(HasContext):

    @on_gather_context.register(priority=10)
    @classmethod
    def _provide_special_value(cls, caller, *, ctx):
        return {'key': 'foo', 'key2': 'hello'}


def test_handler_class_registration():

    e = MyEntity(locals={'key': 'bar'})
    ctx = e.gather_context()
    assert ctx['key'] == 'bar', "works as expected with locals"
    assert ctx['key2'] == 'hello', "init subclass registration works"
