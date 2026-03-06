from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Iterator

from tangl.core import Graph  # noqa: F401  # ensure forward ref availability
from tangl.story.concepts import Concept

if TYPE_CHECKING:
    from .role import Role

class Actor(Concept):
    """
    The Actor class extends the StoryNode class and represents a character or entity
    within the narrative.

    Higher order character features like demographics, look, and outfit are delegated to
    associated resource nodes with their own handlers or managers defined in the
    `tangl.mechanics` subpackage.
    """

    # todo: need an "on associate" handler that triggers when a dep or affordance gets filled
    #       need a guard for if this concept is available and allowed to fill another role

    # todo: this is actually a lang.personal_name
    name: Optional[str] = None

    @property
    def roles(self) -> Iterator[Role]:
        # Scene roles that this actor is associated with
        from .role import Role
        return self.edges_in(is_instance=Role)

    # # @on_can_associate.register()
    # def _can_associate_role(self, other: Role, **kwargs):
    #     if other in self.roles:
    #         raise ValueError("Actor is already in this role")
    #     return True
