from enum import Enum

from pydantic import BaseModel, Field

from tangl.type_hints import Tag
from tangl.core.entity import Entity
from tangl.core.handlers import on_gather_context, on_render_content

class HasSimpleAssets(Entity):
    """
    Adds a tags-like inventory (`inv`) field to any story node for holding simple,
    un-typed and non-associating assets represented as strings or Enums (`Tags`).

    player.inv.add('sword')
    if 'sword' in player.inv: ...
    if player.has_inv('sword', 'shield'): ...
    """

    inv: set[Tag] = Field(default_factory=set)
    # re-uses tags/with_tags validators

    def has_inv(self, *items: Tag) -> bool:
        return self._attrib_is_superset_of("inv", *items)

    @on_gather_context.register()
    def _include_inv_items(self, **kwargs):
        return {"inv": self.inv}
