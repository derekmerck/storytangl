from typing import Iterator, Iterable, Self
import logging

from tangl.core import CallReceipt, Entity, Registry
from tangl.core.dispatch import HasLocalBehaviors
from tangl.core.registry import VT
from tangl.core.dispatch.core_dispatch import core_dispatch, ContextP, on_index

logger = logging.getLogger(__name__)


# Example of feature hooks in multiple layers
class HookedRegistry(Registry, HasLocalBehaviors):

    def do_index(self: Self, item: Entity, *, ctx=None, extra_handlers=None, **kwargs) -> Iterator[CallReceipt]:
        # Convenience entry-point
        return core_dispatch.dispatch(
            # behavior ctx
            caller=self,
            ctx=ctx,
            with_args=(item,),
            with_kwargs=kwargs,

            # dispatch meta
            task="index",
            extra_handlers=extra_handlers,
        )

    def add(self, item: VT, extra_handlers: Iterable = None) -> None:
        logger.debug(f"{self!r}:add: Adding {item!r}")
        receipts = self.do_index(item, ctx=None, extra_handlers=extra_handlers)
        list(receipts)  # evaluate the receipts
        super().add(item)

    # class behaviors are added the registry for the level where
    # the class is defined
    @on_index()
    def _log_item_cls(self: Self, item, *, ctx: ContextP = None):
        logger.debug(f"{self!r}:inst/global: indexed {item!r}")

    # local/instance behaviors are registered directly on the class
    @HasLocalBehaviors.register_local(task="index")
    def _log_item_inst(self, item: Entity, *, ctx: ContextP = None):
        logger.debug(f"{self!r}:inst/local: indexed {item!r}")

def _log_item_static(caller: HookedRegistry, item: Entity, *, ctx: ContextP = None):
    logger = logging.getLogger(__name__)
    logger.debug(f"{caller!r}:static/local: indexed {item!r}")

# This adds it to the class local behaviors as a static handler
HookedRegistry.local_behaviors.add_behavior(_log_item_static, task="index")

logging.basicConfig(level=logging.DEBUG)
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

# No example of a local layer inst on owner, I couldn't think of one

# todo: decorators don't like registering class functions, bc they don't match
#       the HandlerFunc protocol

