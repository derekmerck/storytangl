from typing import TYPE_CHECKING
from uuid import UUID

import pydantic
from pydantic import Field

from tangl.type_hints import StringMap
from tangl.utils.inheritance_aware import InheritanceAware
from tangl.core.handler import BaseHandler
from tangl.core.graph import Graph, Node
from tangl.core.entity.handlers import Lockable, HasNamespace, NamespaceHandler
from tangl.core.graph.handlers import TraversableGraph, HasScopedNamespace, AssociatingLink
from tangl.journal import JournalingGraph

from tangl.core.entity.handlers import HasTags
from .player import Player

if TYPE_CHECKING:
    from .world import World
    from tangl.user import User
else:
    from tangl.core.entity import SingletonEntity as World
    from tangl.core.entity import Entity as User

# Note JournalingGraph must come first in mro b/c it expects TraversableGraph for super().enter()
class Story(JournalingGraph, TraversableGraph, HasNamespace, Graph):

    player: Player = Field(default_factory=Player)
    world: World = None
    user: User | UUID = None
    steps: int = 0
    # "steps" may be counted however you like, like on every 'do_action', on exiting a scene, on rollover triggers.

    @property
    def label(self) -> str:
        if self.world:
            return self.world.label

    # journal: Journal = None  # from JournalingGraph
    # history: History = None  # from HasHistory

    @NamespaceHandler.strategy()
    def _include_nodes_by_path_in_ns(self, **kwargs) -> StringMap:
        return {'nodes': self._nodes_by_path}

    @NamespaceHandler.strategy()
    def _include_player_in_ns(self, **kwargs) -> StringMap:
        return {'player': self.player}

    @BaseHandler.strategy("on_get_story_info")
    def _include_turn(self, **kwargs) -> StringMap:
        return {"steps": self.steps}

class _StoryNode(HasTags, InheritanceAware, Lockable, HasScopedNamespace):

    graph: TraversableGraph = Field(default_factory=Story, json_schema_extra={'cmp': False})

    @property
    def story(self) -> TraversableGraph:
        return self.graph

    @property
    def world(self) -> World:
        return self.story.world


StoryNode = pydantic.create_model("StoryNode", __base__=(_StoryNode, Node))
StoryLink = pydantic.create_model("StoryLink", __base__=(_StoryNode, AssociatingLink))
