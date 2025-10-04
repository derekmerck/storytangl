from tangl.core import Node, HasContext
# from tangl.story.asset.simple_assets import HasSimpleAssets

class Player(HasContext, Node):
    pass

from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import Field

from tangl.type_hints import Tags
from tangl.entity.mixins import HasNamespace
from tangl.core import Node
from tangl.graph.mixins import UsesPlugins
from tangl.lang.personal_name import PersonalName
from tangl.lang.gens import Gens
from tangl.entity.mixins import NamespaceHandler

if TYPE_CHECKING:
    from tangl.user import User
    from tangl.world import World
    from .story import Story


class Player(HasPersonalName, UsesPlugins, HasNamespace, Node):
    """
    This is Node that looks like a StoryNode but doesn't include the inherited namespace
    mixin b/c graph calls it specifically
    """

    @property
    def label(self):
        return "player"

    full_name: str = "Zmobie Monster"
    gens: Gens = Gens.XY

    @property
    def is_xx(self) -> bool:
        return self.gens is Gens.XX

    @NamespaceHandler.strategy
    def _include_player_in_ns(self):
        # just expose the entire player object, author can keep whatever
        # they like in player attributes
        return { 'player': self }

    cash: int = 0

    inv: Tags = Field(default_factory=set)

    def has_inv(self, *items: Tags) -> bool:
        return set(items).issubset(self.inv)

    achievements_: Tags = Field(default_factory=set, alias="achievements")

    @property
    def achievements(self) -> Tags:
        # include game (local) _and_ user (global) achievements
        if self.user:
            return self.user.achievements()
        return self.achievements_

    def has_achievement(self, *items: Tags) -> bool:
        return set(items).issubset(self.achievements)

    def has(self, *items) -> bool:
        """
        Check for tags, inventory, or achievements.

        Check for achievements in this world with `player.has("my_achievement")`, or
        use `player.has("world_id/my_achievement")` syntax for a foreign world.
        """
        for item in items:
            if self.has_tags(item) or \
               self.has_inv(item) or \
               self.has_achievement(item):
                return True
        return False

    notifications: list[str] = Field(default_factory=list)

    @property
    def story(self) -> 'Story':
        return self.graph

    @property
    def user(self) -> 'User':
        if self.graph and hasattr(self.graph, "user"):
            return self.graph.user

    @property
    def world(self) -> 'World':
        if self.graph and hasattr(self.graph, "world"):
            return self.graph.world

    @property
    def pm(self):
        if hasattr(self.story, "pm"):
            return self.story.pm
