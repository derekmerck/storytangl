# tangl/story/dispatch/story_dispatch.py
from __future__ import annotations
from typing import Iterator, TYPE_CHECKING
from functools import partial

from tangl.core import Node, CallReceipt, BaseFragment
from tangl.core.behavior import HandlerLayer as L, ContextP, LayeredDispatch
from tangl.vm import ResolutionPhase as P

if TYPE_CHECKING:
    from tangl.story.concepts import Concept

story_dispatch = LayeredDispatch(label="story.dispatch", handler_layer=L.APPLICATION)

# Hook vm phase tasks
on_planning = partial(story_dispatch.register, task=P.PLANNING)
on_journal = partial(story_dispatch.register, task=P.JOURNAL)

# Looks like story-layer, but actually core hooks
on_cast_actor = partial(story_dispatch.register, task="link", is_instance='Role')
on_scout_location = partial(story_dispatch.register, task="link", is_instance='Setting')

# Create story-layer sub-tasks, author layer can interact with these
on_render = partial(story_dispatch.register, task="render")      # produce fragments
on_describe = partial(story_dispatch.register, task="describe")  # produce strings
on_journal_content = partial(story_dispatch.register, task="journal_content")
on_relationship_change = partial(story_dispatch.register, task="relationship_change")
on_get_choices = partial(story_dispatch.register, task="get_choices")

# story application-level dispatch
def do_describe(concept: Concept, *,
                ctx: ContextP,
                extra_handlers=None,
                **kwargs) -> Iterator[CallReceipt]:
    return story_dispatch.dispatch(
        concept,
        ctx=ctx,
        task="describe",
        extra_handlers=extra_handlers,
        **kwargs
    )

# @on_story_render(priority=Prio.EARLY)
# # hook vm render task for episodic nodes (cursors are always episodes)
# # Early on, we gather concepts and cache them in the context
# def _describe_concept_dependencies(c: Block, *, ctx):
#     """"
#     setting:
#       abc: Abc is a place where...
#     role:
#       john: John is a friend of yours...
#       april: April is John's daughter...
#     """
#     setattr(ctx, 'concepts', defaultdict(dict))
#     for concept in c.dependencies:
#         # Execute a story level task, higher layers will be invoked, but will
#         # probably ignore it unless they are auditing.
#         ctx.concepts[type(concept)][concept.name] = do_describe(concept, ctx=ctx)
