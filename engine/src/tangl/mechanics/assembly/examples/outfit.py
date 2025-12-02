from __future__ import annotations

from tangl.core import Node
from tangl.lang.body_parts import BodyRegion
from tangl.mechanics.presence.wearable import Wearable
from tangl.mechanics.presence.wearable.enums import WearableLayer
from tangl.mechanics.assembly import HasSlottedContainer, Slot, SlottedContainer


class OutfitManager(SlottedContainer[Wearable]):
    """Manage wearable items across body regions and clothing layers."""

    slots = {
        f"{region.name.lower()}_{layer.value}": Slot(
            name=f"{region.name.lower()}_{layer.value}",
            selection_criteria={
                "predicate": (
                    lambda wearable, r=region, l=layer.value: r in wearable.covers and wearable.layer.value <= l
                )
            },
            max_count=3,
        )
        for region in BodyRegion
        for layer in WearableLayer
    }

    def _validate_custom(self) -> list[str]:
        errors: list[str] = []

        uniform_count = sum(1 for comp in self.all_components() if comp.has_tags("uniform"))
        if 0 < uniform_count < 3:
            errors.append(f"Need 3+ uniform pieces (have {uniform_count})")

        for region in BodyRegion:
            items_here = [component for component in self.all_components() if region in component.covers]
            items_here.sort(key=lambda wearable: wearable.layer.value)

            for idx, item in enumerate(items_here[:-1]):
                if getattr(item, "state", None) and item.state.name == "OPEN":
                    covering_item = items_here[idx + 1]
                    if getattr(covering_item, "state", None) and covering_item.state.name == "CLOSED":
                        errors.append(
                            f"{item.label} is open but covered by closed {covering_item.label}"
                        )

        return errors


class OutfitOwner(HasSlottedContainer, Node):
    """Example entity with an attached outfit manager."""

    _container_class = OutfitManager
