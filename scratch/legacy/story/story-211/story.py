from __future__ import annotations
from typing import Optional, TYPE_CHECKING, ClassVar, Callable
import logging

from pydantic import Field

from tangl.graph import Node, Graph
from tangl.entity.mixins import HasNamespace, NamespaceHandler, Lockable
from tangl.graph.mixins import TraversableGraph, TraversalHandler, HasCascadingNamespace, UsesPlugins
from tangl.user import User
from tangl.journal import Journal
from .story_handler import StoryHandler

if TYPE_CHECKING:
    from pluggy import PluginManager
    from tangl.world import World
    from .player import Player

logger = logging.getLogger("tangl.story")
logger.setLevel(logging.WARNING)

class StoryNode(UsesPlugins, HasCascadingNamespace, Lockable, Node):
    """
    User stories are represented as Graph structures. The narrative is driven by traversing Scene and Block nodes using Action edges, generating Journal updates.
    """
    @property
    def story(self) -> Story:
        return self.graph

    @property
    def world(self) -> 'World':
        return self.story.world

    @property
    def pm(self) -> PluginManager:
        if hasattr(self.story, "pm"):
            return self.story.pm

    @property
    def generic(self) -> bool:
        return self.has_tags('generic') or self.locals.get("generic", False)


class Story(UsesPlugins, HasNamespace, TraversableGraph, Graph):
    """
    Extends the TraversableGraph class as a convenient place to store
    metadata about the game state, user account, and world.
    """

    @property
    def world(self) -> 'World':
        return self.factory  # type: World

    @property
    def pm(self) -> PluginManager:
        if self.world:
            return self.world.pm

    # todo: if we detect a titled context change, should set a section bookmark as well

    journal: Journal = Field(default_factory=Journal)

    # Saving this as a regular field since it gets manipulated during serialization
    # and doesn't have the expected 'parent' relationship for a child.
    user: Optional[User] = None

    metadata_: dict = Field(default_factory=dict, alias="metadata")

    @property
    def metadata(self):
        if self.user:
            return self.user.world_metadata.get(self.world.label)
        return self.metadata_

    @property
    def player(self) -> Player:
        from .player import Player
        if x := list(self.find_nodes(Player)):
            return x[0]

    @property
    def turn(self) -> int:
        return self.step_count

    @turn.setter
    def turn(self, value: int):
        self.step_count = value

    dirty: bool = False

    def get_status(self):
        return StoryHandler.get_traversal_status(self)

    # Namespace mixins

    @NamespaceHandler.strategy
    def _include_world_ns(self):
        logger.debug("Checking for world ns")
        if self.world:
            return NamespaceHandler.get_namespace(self.world)

    @NamespaceHandler.strategy
    def _include_user_ns(self):
        logger.debug("Checking for user ns")
        if self.user:
            return NamespaceHandler.get_namespace(self.user)

    @NamespaceHandler.strategy
    def _include_story_metadata(self):
        return {'meta': self.metadata}

    @NamespaceHandler.strategy
    def _include_player_ns(self):
        logger.debug("Checking for player ns")
        if self.player:
            return NamespaceHandler.get_namespace(self.player)

    @NamespaceHandler.strategy
    def _include_top_level_story_nodes(self):
        # Include scenes, actors, places, assets (no "/" in paths)
        top_level_nodes = []
        top_level_nodes.extend( self.get_actors() )
        top_level_nodes.extend( self.get_scenes() )
        res = {v.label: v for v in top_level_nodes}
        logger.debug( f"Including top level objs in ns: {list(res.keys())}")
        return res

    @NamespaceHandler.strategy
    def _include_story_turn(self):
        return { 'turn': self.turn }

    @NamespaceHandler.strategy
    def _include_dirty(self):
        return { 'dirty': self.dirty }

    # Traversal Entry Scene
    @TraversalHandler.enter_strategy
    def _find_entry_node(self, **kwargs):
        logger.debug('Trying to find entry scene (Story)')
        if not self.cursor:
            candidates = self.get_scenes( filt=lambda x: x.is_entry and x.available() )
            if not candidates:
                raise RuntimeError("Unable to infer an entry node for the graph traversal")
            self.cursor = candidates[0]
        logger.debug(f"Initial cursor: {self.cursor.label}")
        TraversalHandler.enter( self.cursor )
    # _find_entry_node.strategy_priority = 85  # _after_ rendering your own title

    # Utility functions
    def get_scenes(self, filt: Callable = None):
        from .scene import Scene
        return self.find_nodes( Scene, filt )

    def get_actors(self, filt: Callable = None):
        from .actor import Actor
        return self.find_nodes( Actor, filt )
