from __future__ import annotations
from typing import Optional, TYPE_CHECKING

# from tangl.core import Associating, Renderable, on_associate, on_disassociate, on_can_associate, on_can_disassociate
# from tangl.story.story_node import StoryNode
from tangl.core.services import Renderable

if TYPE_CHECKING:
    from .role import Role

class Actor(Renderable):
    """
    The Actor class extends the StoryNode class and represents a character or entity
    within the narrative.

    Higher order character features like demographics, look, and outfit are delegated to
    associated resource nodes with their own handlers or managers defined in the
    `tangl.mechanics` subpackage.
    """

    name: Optional[str] = None

    @property
    def roles(self) -> list[Role]:
        # Scene roles that this actor is associated with
        # Note, actors should _not_ be initialized with a list of roles,
        # their roles should be updated through the association handler as they
        # are cast and uncast.
        from .role import Role
        return self.find_children(has_cls=Role)

    def describe(self):
        ...

    # @on_can_associate.register()
    def _can_associate_role(self, other: Role, **kwargs):
        if other in self.roles:
            raise ValueError("Actor is already in this role")
        return True
