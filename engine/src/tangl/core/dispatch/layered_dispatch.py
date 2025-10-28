"""Dispatch Layers
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

5. user
- ancestors (_this_ graph)
- structure (_this path_)

6. inline

-----

Lower levels can plug into tasks defined at higher levels or define new tasks.
Higher levels should not make any assumptions about lower level task definitions.

Higher level invocations should admit lower level layers
"""
# --------------------------
# tangl/core/dispatch/core_dispatch.py
from functools import partial
from typing import Iterator, Iterable, Protocol, Self
import logging

from tangl.type_hints import StringMap
from tangl.core import BehaviorRegistry, CallReceipt, Node, Entity, Registry
from tangl.core.dispatch import HandlerLayer as L, HasLocalBehaviors
from tangl.core.registry import VT

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class ContextP(Protocol):
    # ctx can ordinarily be anything, for 5-layer dispatch, it should implement:
    # - get_job_layers() -> behavior registries applicable to this context (sys, app, author)
    # - get_local_layers()  -> ancestor and domain layers relevant to _this_ caller/graph

    def get_job_layers(self) -> Iterable[BehaviorRegistry]: ...
    # Get [system, application, and author] registries for this context
    # global/core is fixed, local is expanded separately, inline is managed in func
    def get_local_layers(self) -> Iterable[Entity]: ...  # or Domain or whatever

class LayeredDispatch(BehaviorRegistry):

    def dispatch(self, *,
                 # Behavior params
                 caller: Entity,                    # Active entity
                 others: tuple[Entity, ...] = None, # Other participating entities
                 ctx: ContextP = None,              # Includes get_job_layers
                 params: StringMap = None,

                 # Dispatch meta
                 task = None,  # alias for `inline_criteria[has_task]`
                 inline_criteria: StringMap = None,
                 extra_handlers = None,
                 dry_run = False) -> Iterator[CallReceipt]:

        # logger.debug(f"{self!r} Dispatch called")

        # --------------------
        # Assemble layer model

        # core_dispatch is _always_ included
        layers = {core_dispatch, self}  # self _may_ be core dispatch
        if ctx and hasattr(ctx, "get_active_layers"):
            ctx_layers = ctx.get_active_layers()
            layers.update(ctx_layers)
        if hasattr(caller, "local_behaviors"):
            layers.add(caller.local_behaviors)
        # extra handlers are passed along and act as the INLINE layer

        # logger.debug(f"Dispatch layers: {layers!r}")

        # --------------------
        # Invoke on chained layers
        receipts = self.chain_dispatch(
            *layers,
            caller=caller,
            others=others,
            ctx=ctx,
            params=params,

            task=task,
            inline_criteria=inline_criteria,
            extra_handlers=extra_handlers,
            dry_run=dry_run
        )

        # --------------------
        # Aggregate or return an iterator
        return CallReceipt.gather_results(*receipts)

core_dispatch = LayeredDispatch(label="core.dispatch", handler_layer=L.GLOBAL)

# core dispatch hooks, structuring, init, linking on graph, indexing on reg
on_create = partial(core_dispatch.register, task="create")  # cls resolution hook (cls)
on_init   = partial(core_dispatch.register, task="init")    # post-init hook (self)
on_link   = partial(core_dispatch.register, task="link")    # connect nodes (source, dest)
on_index  = partial(core_dispatch.register, task="index")   # on registry add (reg, item)

# Core dispatch may have helpers, auditors, or other features; but lower
# layer tasks should never invoke or register with the core_dispatch directly,
# just inject it as a layer into its own task.
# If core _wants_ to define an application-specific handler, like an auditor
# for the vm "planning" task, that's fine, but it none of vm's business.
# vm will invoke it automatically along with core_dispatch.

# --------------------
# Example - on_index w locals

def do_index(registry: Registry, item: Entity, *, ctx=None, extra_handlers=None, params=None) -> Iterator[CallReceipt]:
    # Convenience entry-point
    return core_dispatch.dispatch(
        # behavior ctx
        caller=registry,
        others=(item,),
        ctx=ctx,
        params=params,

        # dispatch meta
        task="index",
        extra_handlers=extra_handlers,
    )

# Example of feature hooks in multiple layers
class HookedRegistry(Registry, HasLocalBehaviors):

    def add(self, item: VT, extra_handlers: Iterable = None) -> None:
        logger.debug(f"{self!r}:add: Adding {item!r}")
        receipts = do_index(self, item, ctx=None, extra_handlers=extra_handlers)
        super().add(item)

    # class behaviors are added the registry for the level where
    # the class is defined
    @on_index()
    def _log_item_cls(self: Self, item, *, ctx: ContextP = None):
        logger.debug(f"{self!r}:inst/global: indexed {item!r}")

    # local/instance behaviors are registered directly on the class
    @HasLocalBehaviors.register_local(task="index")
    def _log_item_inst(self, other, *, ctx: ContextP = None):
        logger.debug(f"{self!r}:inst/local: indexed {other!r}")

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

exit()

# --------------------------
# vm.planning
from typing import Iterator
from functools import partial

from tangl.core import Behavior, BehaviorRegistry  # core_dispatch
from tangl.core.dispatch import HandlerPriority as Prio
from tangl.vm import Context, ResolutionPhase as P
vm_dispatch = BehaviorRegistry(label="vm.dispatch", handler_layer=L.SYSTEM)

# When creating a dispatch, we might enumerate the default layers _above_ that it should include in every call.
# Then derive the layers below from the ctx, and override upper layers if needed

# vm phase dispatch registration hooks
on_validate = partial(vm_dispatch.register, task=P.VALIDATE)
on_planning = partial(vm_dispatch.register, task=P.PLANNING)
on_prereq   = partial(vm_dispatch.register, task=P.PREREQS)
on_update   = partial(vm_dispatch.register, task=P.UPDATE)
on_journal  = partial(vm_dispatch.register, task=P.JOURNAL)
on_finalize = partial(vm_dispatch.register, task=P.FINALIZE)
on_postreq  = partial(vm_dispatch.register, task=P.POSTREQS)

# Lower layer tasks should never invoke the phase dispatch directly, instead
# add an application layer dispatch like "on_story_planning" that indicates
# task "planning", application layer dispatch will be passed in by the phase
# handler.

@on_planning(priority=Prio.EARLY)
def _get_offers(c, *, ctx) -> 'Offers':
    # stash offers per dep in context
    ...

@on_planning(priority=Prio.LATE)
def _accept_offers(c, *, ctx) -> CallReceipt:
    # review offers and accept for each dep
    ...

# vm system-level dispatch
def do_planning(cursor: Node, *, ctx: ContextP, extra_handlers=None, **kwargs) -> Iterator[CallReceipt]:
    return vm_dispatch.dispatch(
        cursor,
        ctx=ctx,
        active_layer=vm_dispatch,
        task=P.PLANNING,
        extra_handlers=extra_handlers,
        **kwargs
    )

# ------------------
# tangl.story import story_dispatch
story_dispatch = BehaviorRegistry(label="story.dispatch", handler_layer=L.APPLICATION)

# Hook vm phase tasks
on_story_planning = partial(story_dispatch.register, task="planning")
on_story_render = partial(story_dispatch.register, task="render")

# Looks like story-layer, but actually core hooks
on_cast_actor = partial(story_dispatch.register, task="link", is_instance='Role')
on_scout_location = partial(story_dispatch.register, task="link", is_instance='Setting')

# Create story-layer sub-tasks
on_describe = partial(story_dispatch.register, task="describe")
on_relationship_change = partial(story_dispatch.register, task="relationship_change")

@on_story_planning()
def _provide_concept_offers(caller: Node, *, ctx=Context) -> "Offers":
    ...

@on_story_planning()
def _provide_episode_offers(caller: Node, *, ctx=Context) -> "Offers":
    ...

from typing import Type

# should be an on_story_create()?  Or do we just want to hook the global handler?
@on_create(is_subclass=Node)  # fires if c is a type, and it is Node or a subclass of Node
def _use_node_plus(c: Type, *, ctx=None):
    # One of the few dispatches where the caller item is _not_ an Entity, it's a Type
    class NodePlus(Node):
        ...
    return NodePlus
    # Should only return a subclass of the is_subclass criteria

from collections import defaultdict

from tangl.story.concepts import Concept
from tangl.story.episode import Block

@on_describe(is_instance=Concept)
def _provide_concept_description(c, *, ctx):
    return { c.name: c.describe() }
    # do we want to pass args for the kind of description?

# story application-level dispatch
def do_describe(concept: Concept, *,
                ctx: ContextP,
                extra_handlers=None,
                **kwargs) -> Iterator[CallReceipt]:
    return LayeredDispatch.layered_dispatch(
        concept,
        ctx=ctx,
        active_layer=story_dispatch,
        extra_handlers=extra_handlers,
        **kwargs
    )

@on_story_render()  # hook vm render task for episodic nodes (cursors are always episodes)
def _provide_dependent_concept_descriptions(c: Block, *, ctx):
    """"
    setting:
      abc: Abc is a place where...
    role:
      john: John is a friend of yours...
      april: April is John's daughter...
    """
    result = defaultdict(dict)
    for concept in c.dependencies:
        result[type(concept)][concept.name] = do_describe(concept, ctx=ctx)
    return result
