# tangl/core/dispatch/hooked_registry.py
from typing import Iterator, Iterable, Self
import logging
from functools import partial

from tangl.core import Entity, Registry
from tangl.core.registry import VT
from tangl.core.behavior.call_receipt import CallReceipt
from tangl.core.behavior.has_behaviors import HasLocalBehaviors
from tangl.core.behavior.layered_dispatch import ContextP
from .core_dispatch import core_dispatch
from .hooked_entity import HookedEntity

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Used in hooked registry
on_index  = partial(core_dispatch.register, task="index")   # add item to registry (reg, item)

# Example of feature hooks in multiple layers
class HookedRegistry(Registry, HookedEntity, HasLocalBehaviors):

    def do_index(self: Self, item: Entity, *, ctx: ContextP = None, extra_handlers=None, **kwargs) -> Iterator[CallReceipt]:
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
