import logging
from idlelib.run import MyHandler

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.handler import on_gather_context, HandlerRegistry, HasContext

logging.basicConfig(level=logging.DEBUG)

class MyEntity(HasContext, Entity):

    @HandlerRegistry.mark_register(priority=10)
    def _provide_special_value(self, ctx):
        return {'key': 'foo'}


def test_handler_registry_deferred_registration():
    # HasContext specifically calls register_marked_handlers on itself when subclasses
    # are added.  Currently, deferred registration is _not_ supported for other handler
    # types bc we would need to come up with a discriminator annotation to signal each
    # registry instance which functions to attend to.  So this should be considered fragile.

    on_gather_context.register_marked_handlers(MyEntity)

    e = MyEntity(locals={'key': 'bar'})
    assert e.gather_context()['key'] == 'bar', "works as expected with locals"

    e = MyEntity()
    assert e.gather_context()['key'] == 'foo', "default post-registration handler works"
