from __future__ import annotations
from typing import Optional, Iterable, TYPE_CHECKING

from tangl.core.entity import Node
from tangl.core.handlers import Renderable
# Associating, on_associate, on_disassociate, on_can_associate, on_can_disassociate
from ..actor import Extras

if TYPE_CHECKING:
    from .setting import Setting

# originally "location -> concrete place", refactored to "setting -> concrete location"

class Location(Renderable, Node):

    # todo: mixin 'HasExtras' and initial casting

    name: Optional[str] = None

    @property
    def settings(self) -> list[Setting]:
        # Scene settings that this loc is associated with
        # Note, locations should _not_ be initialized with a list of settings,
        # their settings should be updated through the association handler as they
        # are scouted and unscouted.
        from .setting import Setting
        return self.find_children(has_cls=Setting)

    @property
    def extras(self) -> list[Extras]:
        return self.find_children(has_cls=Extras)

    def describe(self):
        ...

    # @on_can_associate.register()
    def _can_associate_setting(self, other: Setting, **kwargs):
        if other in self.settings:
            raise ValueError("Location is already in this setting")
        return True
