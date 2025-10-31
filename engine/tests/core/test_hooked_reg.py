import logging
from typing import Self

from tangl.core import Entity, Registry
from tangl.core.behavior import HasLocalBehaviors
from tangl.core.dispatch import HookedRegistry as _HookedRegistry, on_index

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

class HookedRegistry(_HookedRegistry):

    # class behaviors are added the registry for the level where
    # the class is defined
    @on_index()
    def _log_item_cls(self: Self, item, *_, **__):
        logger.debug(f"{self!r}:inst/global: indexed {item!r}")

    # local/instance behaviors are registered directly on the class
    @HasLocalBehaviors.register_local(task="index")
    def _log_item_inst(self, item: Entity, *_, **__):
        logger.debug(f"{self!r}:inst/local: indexed {item!r}")

def _log_item_static(caller: HookedRegistry, item: Entity, *_, **__):
    logger = logging.getLogger(__name__)
    logger.debug(f"{caller!r}:static/local: indexed {item!r}")

    # This adds it to the class local behaviors as a static handler

HookedRegistry.local_behaviors.add_behavior(_log_item_static, task="index")

# todo: decorators don't like registering class functions, bc they don't match the HandlerFunc protocol

# todo: asserts on debug log??  Rewrite w concrete output??

def test_hooked_reg():
    logging.debug("------------------")

    hooked_registry = HookedRegistry(label="r1")
    item = Entity(label="item")
    hooked_registry.add(item, extra_handlers=[lambda a, b, ctx: logger.debug(f"{a!r}:lambda: indexed {b!r}")])

    """
    DEBUG:__main__:<HookedRegistry:r1>:add: Adding <Entity:item>
    DEBUG:__main__:<HookedRegistry:r1>:inst/global: indexed <Entity:item>
    DEBUG:__main__:<HookedRegistry:r1>:inst/local: indexed <Entity:item>
    DEBUG:__main__:<HookedRegistry:r1>:static/local: indexed <Entity:item>
    DEBUG:__main__:<HookedRegistry:r1>:lambda: indexed <Entity:item>
    """
    logging.debug("------------------")

    hooked_registry2 = HookedRegistry(label="r2")
    hooked_registry2.add(item)
    # Add + same 3 funcs called, but not lambda

    """
    DEBUG:__main__:<HookedRegistry:r2>:add: Adding <Entity:item>
    DEBUG:__main__:<HookedRegistry:r2>:inst/global: indexed <Entity:item>
    DEBUG:__main__:<HookedRegistry:r2>:inst/local: indexed <Entity:item>
    DEBUG:__main__:<HookedRegistry:r2>:static/local: indexed <Entity:item>
    """
    logging.debug("------------------")

    registry = Registry(label='r3')
    registry.add(item)
    # Nothing

    logging.debug("------------------")

    class HookReg4(HookedRegistry):
        ...

    hooked_registry4 = HookReg4(label="r4")
    hooked_registry4.add(item)
    # only global, doesn't inherit local behaviors
    """
    DEBUG:__main__:<HookReg4:r4>:add: Adding <Entity:item>
    DEBUG:__main__:<HookReg4:r4>:inst/global: indexed <Entity:item>
    """

    # todo: No example of a local layer inst on owner, I couldn't think of one
