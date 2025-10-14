from __future__ import annotations
import logging

from pydantic import Field

from tangl.type_hints import StringMap
# from tangl.graph.mixins import AssociationHandler
# from tangl.story.story import StoryNode
from .role import Role
from .actor import Actor

logger = logging.getLogger(__name__)


class Extras(Role):
    """
    Extra is an extension of role that can generate batches of random generic actors according
    to a template.

    Similar to a :class:`tangl.actor.Role`, but requires a template and returns a
    list of generic/transient :class:`Actors<tangl.actor.Actor>` that can be assigned
    manually to jobs or roles.

    Extras is a subtype of Role for dynamically generated stock actors.
    They are generated in batches rather than individually and only support templates.
    Extras can be identified by a "generic" flag in their local variables.
    """
    # todo: need to flag these for some kind of eventual garbage collection unless
    #       they get used somewhere and promoted to 'semi-generic' or something...

    # _Required_
    successor_template: StringMap = Field(..., alias='actor_template')

    # todo: some extension to reuse generics that were generated previously?  Eventually a generic that appears several times becomes a permanent-generic

    def cast(self, n: int = 3) -> list[Actor]:
        result = []
        for i in range(n):
            extra = super().cast()
            extra.tags.add('generic')
            result.append(extra)
        return result

    def uncast(self):
        raise RuntimeError("Cannot uncast extras, just discard them from the graph.")

    def associate_with(self, actor: Actor, **kwargs):
        # No need to associate or disassociate with extras roles?
        pass


    @property
    def label(self):
        super_label = StoryNode.label.fget(self)
        if super_label and not super_label.startswith("ex-"):
            return f"ex-{super_label}"
        return super_label

    #: _Must_ have a template
    actor_template: dict = Field(...)

    count: int | tuple[int, int] = [1, 3]

    def cast(self, count: int | tuple[int, int] = 1) -> list[Actor]:
        count = count or self.count

        res = []
        for i in range(0, count):
            CastingHandler.cast(self)    # associates a new actor
            res.append( self.actor )
            CastingHandler.uncast(self)  # disassociate
        return res

    # @AssociationHandler.associate_with_strategy
    # def _finalize_actor(self, extra: Actor, **kwargs):
    #     extra.label_ += f"-{str(extra.uid)[0:3]}"
    #     extra.tags.add('generic')
    #     logger.debug( str(extra) )
    #     # actor.locals['generic'] = True  # alternative tagging

