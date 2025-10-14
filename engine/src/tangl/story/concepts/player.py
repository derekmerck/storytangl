from __future__ import annotations
from typing import TYPE_CHECKING

# from tangl.story.asset.simple_assets import HasSimpleAssets

from pydantic import Field

from tangl.core import Node
from tangl.type_hints import Tag
from tangl.core import Node
from tangl.lang.personal_name import PersonalName
from tangl.lang.gens import Gens

if TYPE_CHECKING:
    from tangl.service.user import User
    from tangl.story.fabula import World

class Player(PersonalName, Node):
    """
    This is Node that looks like a StoryNode but doesn't include the inherited namespace
    mixin b/c graph calls it specifically
    """

    @property
    def label(self):
        return "player"

    full_name: str = "T. Angld Ev"
    gens: Gens = Gens.XY

    @property
    def is_xx(self) -> bool:
        return self.gens is Gens.XX

    # @NamespaceHandler.strategy
    def _include_player_in_ns(self):
        # just expose the entire player object, author can keep whatever
        # they like in player attributes
        return { 'player': self }

    cash: int = 0

    inv: set[Tag] = Field(default_factory=set)

    def has_inv(self, *items: Tag) -> bool:
        return set(items).issubset(self.inv)

    achievements_: set[Tag] = Field(default_factory=set, alias="achievements")

    @property
    def achievements(self) -> list[Tag]:
        # include game (local) _and_ user (global) achievements
        if self.user:
            return self.user.achievements()
        return self.achievements_

    def has_achievement(self, *items: Tag) -> bool:
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
