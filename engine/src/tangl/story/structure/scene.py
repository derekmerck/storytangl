
from tangl.core import HasEffects, HasConditions, TraversableNode, on_gather_context

from ..story_node import StoryNode
from ..concept.actor import Role
from ..concept.location import Setting
from .block import Block

class Scene(HasConditions, HasEffects, TraversableNode, StoryNode):

    @property
    def settings(self) -> list[Setting]:
        # These are indirect links to Places
        return self.find_children(has_cls=Setting)

    @property
    def roles(self) -> list[Role]:
        # These are indirect links to Actors
        return self.find_children(has_cls=Role)

    @property
    def blocks(self) -> list[Block]:
        return self.find_children(has_cls=Block)

    @on_gather_context.register()
    def _provide_actors(self, **context):
        res = {}
        if len(self.roles) == 1:
            res['actor'] = self.roles[0].successor
        res |= { v.label: v.successor for v in self.roles if v.successor is not None }
        return res or None

    @on_gather_context.register()
    def _provide_places(self, **context):
        res = {}
        if len(self.settings) == 1:
            res['location'] = self.settings[0].successor
        res |= { v.label: v.successor for v in self.settings if v.successor is not None }
        return res or None

    @on_gather_context.register()
    def _provide_self(self, **context):
        return { 'scene': self }
