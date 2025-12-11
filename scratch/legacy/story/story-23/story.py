from __future__ import annotations
import typing
from typing import Optional
from uuid import UUID, uuid4
from collections import ChainMap

import attr
import pluggy

from tangl.core import Index
from tangl.core import TraversableMixin
from tangl.story.scene import Scene
from tangl.user import User
from .update_handler import UpdateHandler
from .player import Player

if typing.TYPE_CHECKING:
    from tangl.world import World
else:
    World = object

@attr.s(init=False)
class Story(Index):
    """
    Extends the core Index class as a convenient place to store
    metadata about the game state, account, and world.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.__attrs_init__(*args, **kwargs)
        self.player._index = self
        if not self.player.metadata:
            self.player.metadata['achievements'] = set()
            self.player.metadata['playthroughs'] = 0
        if self.pm is not None:
            self.pm.hook.on_init_story(story=self)


    guid: UUID = attr.ib(factory=uuid4,
                         converter=lambda x: x if isinstance(x, UUID) else UUID(x))
    @property
    def uid(self) -> str:
        return str(self.guid)

    @property
    def _path_map(self):
        if self.world.unique_block_ids:
            return { v.uid: v for v in self._nodes.values() } | { v.path: v for v in self._nodes.values() }
        return { v.path: v for v in self._nodes.values() }

    world: World = attr.ib(default=None)

    @property
    def pm(self) -> Optional[pluggy.PluginManager]:
        if self.world is not None:
            return self.world.pm

    user: Optional[User] = attr.ib(default=None)

    bookmark: Optional[TraversableMixin] = attr.ib(default=None)

    locals: dict = attr.ib(factory=dict)
    turn: int = attr.ib(default=0)

    player: Player = attr.ib()
    @player.default
    def _mk_player(self):
        # trigger automorph factory, so it sets parent and correct class
        p = Player.from_dict({'index': self})
        return p

    def ns(self) -> ChainMap:
        maps = []
        if self.world is not None:
            world_ns = self.world.ns()
            maps.append( world_ns )
        if self.user is not None:
            user_ns = self.user.ns()
            maps.append( user_ns )
        story_ns = { 'find': lambda key: self.find(key),
                     'player': self.player }
        maps.extend( [ self.locals, story_ns ] )
        if self.pm is not None:
            hook_ns = self.pm.hook.on_get_story_ns(story=self) # this is a list of dicts
            maps.extend( hook_ns )
        return ChainMap(*reversed(maps))


    @property
    def entry_scene(self):
        entry_scenes = [scene for scene in self.scenes
                        if scene.is_entry or scene.uid == "main_menu"]
        if not entry_scenes:
            raise ValueError(f"No entry scene found in story {self.world.uid}")
        if len(entry_scenes) > 1:
            raise ValueError("Multiple entry scenes in story. Only one entry scene is allowed.")
        return entry_scenes[0]

    update_handler: UpdateHandler = attr.ib(factory=UpdateHandler, init=False, repr=False, eq=False)

    def enter(self, **kwargs):
        self.update_handler.start_update()
        self.bookmark = self.entry_scene.enter(**kwargs)
        # start at the entry scene's entry block
