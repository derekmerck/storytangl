# tangl/core/dispatch/core_dispatch.py
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

5. user
- ancestors (_this_ graph)
- structure (_this path_)

6. inline

-----

Lower levels can plug into tasks defined at higher levels or define new tasks.
Higher levels should not make any assumptions about lower level task definitions.

Higher level invocations should admit lower level layers
"""
from functools import partial
from typing import Iterator, Iterable, Protocol, Self
import logging

from tangl.type_hints import StringMap
from tangl.core import BehaviorRegistry, CallReceipt, Node, Entity, Registry
from tangl.core.dispatch import HandlerLayer as L, HasLocalBehaviors
from tangl.core.registry import VT

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# --------------------------
# Context Protocol

class ContextP(Protocol):
    # ctx can ordinarily be anything, for 5-layer dispatch, it should implement:
    # - get_job_layers() -> behavior registries applicable to this context (sys, app, author)
    # - get_local_layers()  -> ancestor and domain layers relevant to _this_ caller/graph

    def get_job_layers(self) -> Iterable[BehaviorRegistry]: ...
    # Get [system, application, and author] registries for this context
    # global/core is fixed, local is expanded separately, inline is managed in func
    def get_local_layers(self) -> Iterable[Entity]: ...  # or Domain or whatever

# --------------------------
# Layered Dispatch Behavior Registry

class LayeredDispatch(BehaviorRegistry):

    def dispatch(self,
                 # Behavior params
                 caller: Entity, *,                    # Active entity
                 ctx: ContextP,                        # Includes get_job_layers
                 with_args: tuple[Entity, ...] = None, # Other participating entities
                 with_kwargs: StringMap = None,

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


# --------------------------
# Core dispatch and convenience decos

core_dispatch = LayeredDispatch(label="core.dispatch", handler_layer=L.GLOBAL)

# Used in HookedEntity for structuring and __post_init__
on_create = partial(core_dispatch.register, task="create")  # cls and kwargs resolution (unstructured data)
on_init   = partial(core_dispatch.register, task="init")    # post-init hook (self)
# Used in HookedGraph when adding or removing an edge
on_link   = partial(core_dispatch.register, task="link")    # connect nodes (source, dest)
on_unlink = partial(core_dispatch.register, task="unlink")  # disconnect nodes (source, dest)
# Used in hooked registry
on_index  = partial(core_dispatch.register, task="index")   # on registry add (reg, item)

# Core dispatch may have helpers, auditors, or other features; but lower
# layer tasks should never invoke or register with the core_dispatch directly,
# just inject it as a layer into its own task.
# If core _wants_ to define an application-specific handler, like an auditor
# for the vm "planning" task, that's fine, but it none of vm's business.
# vm will invoke it automatically along with core_dispatch.

# see `tangl/dispatch/hooked_registry.py` for a registry that uses the `on_index` hook and provides a local layer behavior registry.

# see `tangl/vm/vm_dispatch.py` for an example of a system layer registry and features.

# --------------------------
# /tangl/vm/vm_dispatch.py
from typing import Iterator
from functools import partial

from tangl.core import Behavior, BehaviorRegistry  # core_dispatch
from tangl.core.dispatch import HandlerPriority as Prio
from tangl.vm import Context, ResolutionPhase as P
vm_dispatch = BehaviorRegistry(label="vm.dispatch", handler_layer=L.SYSTEM)

# vm phase dispatch registration hooks
# We can use enums for tasks since we have them
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

# Create story-layer sub-tasks, author layer can interact with these
on_describe = partial(story_dispatch.register, task="describe")
on_relationship_change = partial(story_dispatch.register, task="relationship_change")

@on_story_planning()
def _provide_concept_offers(caller: Node, *, ctx=Context) -> "Offers":
    ...

@on_story_planning()
def _provide_episode_offers(caller: Node, *, ctx=Context) -> "Offers":
    ...

from typing import Type
from collections import defaultdict

from tangl.core.dispatch import HandlerPriority as Prio
from tangl.story.concepts import Concept
from tangl.story.episode import Block
from tangl.journal.content import ContentFragment

# should be an on_story_create()?  Or do we just want to hook the global handler?
@on_create(is_subclass=Node)  # fires if c is a type, and it is Node or a subclass of Node
def _use_node_plus(c: Type, *, ctx=None):
    # One of the few dispatches where the caller item is _not_ an Entity, it's a Type
    class NodePlus(Node):
        ...
    return NodePlus
    # Should only return a subclass of the is_subclass criteria

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

@on_story_render(handler_priority=Prio.EARLY)
# hook vm render task for episodic nodes (cursors are always episodes)
# Early on, we gather concepts and cache them in the context
def _provide_dependent_concept_descriptions(c: Block, *, ctx):
    """"
    setting:
      abc: Abc is a place where...
    role:
      john: John is a friend of yours...
      april: April is John's daughter...
    """
    setattr(ctx, 'concepts', defaultdict(dict))
    for concept in c.dependencies:
        # Execute a story level task, higher layers will be invoked, but will
        # probably ignore it unless they are auditing.
        ctx.concepts[type(concept)][concept.name] = do_describe(concept, ctx=ctx)

@on_story_render(handler_priority=Prio.LATE)
def _compose_fragments(c: Block, *, ctx):
    results = [ContentFragment(**c) for c in ctx.concepts.values()]
    return results
