from __future__ import annotations

from tangl.core import Node
from tangl.mechanics.assembly import HasSlottedContainer
from tangl.mechanics.presence.outfit import OutfitManager


class OutfitOwner(HasSlottedContainer, Node):
    """Example entity with an attached outfit manager."""

    _container_class = OutfitManager
