# tangl/story/story_dispatch.py
from typing import Iterator
from functools import partial

from tangl.core import BehaviorRegistry, Node
from tangl.core.dispatch import HandlerLayer as L, CallReceipt
from tangl.core.dispatch.core_dispatch import ContextP, on_create, LayeredDispatch

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
def _provide_concept_offers(caller: Node, *, ctx) -> "Offers":
    ...

@on_story_planning()
def _provide_episode_offers(caller: Node, *, ctx) -> "Offers":
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

@on_story_render(priority=Prio.EARLY)
# hook vm render task for episodic nodes (cursors are always episodes)
# Early on, we gather concepts and cache them in the context
def _describe_concept_dependencies(c: Block, *, ctx):
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

@on_story_render(priority=Prio.LATE)
def _compose_fragments(c: Block, *, ctx):
    results = [ContentFragment(**c) for c in ctx.concepts.values()]
    return results
