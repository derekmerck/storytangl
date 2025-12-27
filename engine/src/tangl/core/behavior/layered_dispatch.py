# tangl/core/behavior/layered_dispatch.py
"""
Dispatch Layers
---------------

1. global
- core
- audit

2. system
- vm (frame, context/ns, planning, journal)
- service (response)
- media (special planning)

3. application
- story (concept, episode, fabula)

4. author
- world (_this_ fabula, templates, assets, rules, facts)

5. local/user
- ancestors (_this_ graph)
- structure (_this path_)

6. inline

-----

Lower levels can plug into tasks defined at higher levels or define new tasks.
Higher levels should not make any assumptions about lower level task definitions.

Higher level invocations should admit lower level layers
"""
from typing import Iterator, Iterable, Protocol
import logging

from tangl.type_hints import StringMap
from tangl.core import Entity
from .behavior_registry import BehaviorRegistry
from .call_receipt import CallReceipt

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# --------------------------
# Context Protocol

class ContextP(Protocol):
    """
    The behavior execution context can ordinarily be anything; however, for layered dispatch, it should implement:

    - :func:`get_active_layers()` -> SYSTEM, APPLICATION, and AUTHOR layer behavior registries active in this context

    The GLOBAL layer is fixed (`core_dispatch`). The LOCAL layer, if any, is attached to the caller (`caller.local_dispatch`), and the INLINE layer is injected through function parameters.
    """
    def get_active_layers(self) -> Iterable[BehaviorRegistry]: ...

# --------------------------
# Layered Dispatch Behavior Registry

class LayeredDispatch(BehaviorRegistry):

    def dispatch(self,
                 # Behavior params
                 caller: Entity, *,                    # Active entity
                 ctx: ContextP,                        # Includes get_active_layers
                 with_args: tuple[Entity, ...] = None, # Other participating entities
                 with_kwargs: StringMap = None,

                 # Dispatch meta
                 task = None,  # alias for `inline_criteria[has_task]`
                 inline_criteria: StringMap = None,
                 extra_handlers = None,
                 dry_run = False) -> Iterator[CallReceipt]:
        """
        Dispatch with automatic layer assembly.

        Assembles layers:
        - GLOBAL layer: `core_dispatch`
        - SYSTEM, APPLICATION, AUTHOR layers: `ctx.get_active_layers()`
        - LOCAL layer: `caller.local_dispatch`
        - INLINE layer: `dispatch(extra_handlers=...)`

        Then passes those registries and other parameters through to chain_dispatch.

        .. admonition:: Lazy!
            Remember, dispatch returns a receipt generator!  You have to iterate it
            to create results and produce by-products, e.g., `list(receipts)`.
        """
        # logger.debug(f"{self!r} Dispatch called")

        # --------------------
        # Assemble layer model

        from tangl.core.dispatch.core_dispatch import core_dispatch

        # core_dispatch is _always_ included
        layers = {core_dispatch, self}  # self _may_ be core dispatch
        if ctx and hasattr(ctx, "get_active_layers"):
            # Includes ctx's local behaviors if any
            ctx_layers = ctx.get_active_layers() or []
            logger.debug(f"ctx_layers: {ctx_layers}")
            layers.update(ctx_layers)
        if hasattr(caller, "local_behaviors"):
            # attaching local behaviors to a caller is usually going to be _ad hoc_
            locs = caller.local_behaviors
            if locs:
                layers.add(locs)
        if hasattr(caller.__class__, "cls_behaviors"):
            locs = caller.cls_behaviors
            if locs:
                layers.add(locs)
        # extra handlers are passed along and act as the INLINE layer

        logger.debug(f"Dispatch layers: {layers!r}")

        # --------------------
        # Invoke on chained layers
        receipts = self.chain_dispatch(
            *layers,

            # Behavior invocation
            caller=caller,
            ctx=ctx,
            with_args=with_args,
            with_kwargs=with_kwargs,

            # Dispatch meta params
            task=task,
            inline_criteria=inline_criteria,
            extra_handlers=extra_handlers,
            dry_run=dry_run
        )
        return receipts
