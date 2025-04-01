
from tangl.business.core.handlers import HasEffects, HasConditions, TraversableNode, on_gather_context

from tangl.business.story.story_node import StoryNode
from tangl.business.story.actor import Role
from tangl.business.story.place import Location
from .block import Block

class Scene(HasConditions, HasEffects, TraversableNode, StoryNode):

    @property
    def locations(self) -> list[Location]:
        # These are indirect links to Places
        return self.find_children(has_cls=Location)

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
            res['actor'] = self.roles[0].actor
        res |= { v.label: v.successor for v in self.roles if v.successor is not None }
        return res or None

    @on_gather_context.register()
    def _provide_places(self, **context):
        res = {}
        if len(self.locations) == 1:
            res['place'] = self.locations[0].place
        res |= { v.label: v.successor for v in self.locations if v.successor is not None }
        return res or None

    @on_gather_context.register()
    def _provide_self(self, **context):
        return { 'scene': self }
