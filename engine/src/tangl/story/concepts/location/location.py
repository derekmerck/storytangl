from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING, Iterator

from tangl.core import Graph
from tangl.story.concepts import Concept
from tangl.story.concepts.actor import Extras

if TYPE_CHECKING:
    from tangl.vm.context import Context
    from .setting import Setting

# originally named as "dep location -> concrete place", refactored to "dep setting -> concrete location" b/c I think 'setting' is more common and abstract, and 'location' refers to a specific place.  Filmed "on location" vs. "fantasy setting"

class Location(Concept):

    # todo: need an "on associate" handler that triggers when a dep or affordance gets filled
    #       need a guard for if this concept is available and allowed to fill another role

    name: Optional[str] = None

    @property
    def settings(self) -> Iterator[Setting]:
        # Scene settings that this loc is associated with
        # Note, locations should _not_ be initialized with a list of settings,
        # their settings should be updated through the association handler as they
        # are scouted and unscouted.
        from .setting import Setting
        return self.edges_in(is_instance=Setting)

    @property
    def extras(self) -> Iterator[Extras]:
        return self.edges_out(is_instance=Extras)

    def describe(
        self,
        *,
        ctx: "Context" | None = None,
        ns: dict[str, Any] | None = None,
        **locals_: Any,
    ) -> str | None:
        return super().describe(ctx=ctx, ns=ns, **locals_)

    # @on_can_associate.register()
    # def _can_associate_setting(self, other: Setting, **kwargs):
    #     if other in self.settings:
    #         raise ValueError("Location is already in this setting")
    #     return True
