"""Outfit loadout surface for presence mechanics.

Why
---
`OutfitManager` is a real mechanics building block used by appearance-oriented
facets such as `look`. It belongs in the `presence` family rather than behind an
`assembly.examples` import path.
"""

from __future__ import annotations

from tangl.lang.helpers import oxford_join
from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.mechanics.presence.wearable import Wearable
from tangl.mechanics.presence.wearable.enums import WearableLayer, WearableState


class OutfitManager(ComponentManager[Wearable]):
    """Manage wearable items across body regions and clothing layers.

    Key Features
    ------------
    - Groups wearables by body region and clothing layer.
    - Reuses :class:`tangl.mechanics.assembly.SlottedContainer` for assignment
      and validation semantics.
    - Adds outfit-specific validation such as uniform-piece requirements and
      simple open-versus-covered checks.
    """

    slots = {
        f"{region.name.lower()}_{layer.value}": Slot(
            name=f"{region.name.lower()}_{layer.value}",
            selection_criteria={
                "predicate": (
                    lambda wearable, r=region, layer_value=layer.value: (
                        r in wearable.covers and wearable.layer.value <= layer_value
                    )
                )
            },
            max_count=3,
        )
        for region in BodyRegion
        for layer in WearableLayer
    }

    def components(self) -> list[Wearable]:
        """Return a stable, deduplicated list of assigned wearables."""
        deduped: dict[object, Wearable] = {}
        for component in self.all_components():
            key = getattr(component, "uid", None) or id(component)
            deduped.setdefault(key, component)

        result = list(deduped.values())
        result.sort(
            key=lambda wearable: (
                wearable.layer.value,
                wearable.label or "",
                wearable.noun or "",
            )
        )
        return result

    def describe_items(self) -> list[str]:
        """Return concise wearable labels suitable for prose or prompt adapters."""
        return [
            desc
            for component in self.components()
            if (desc := component.render_desc())
        ]

    def describe(self) -> str:
        """Return a compact phrase describing the current outfit."""
        return oxford_join(self.describe_items())

    def covered_mask(self) -> BodyPart:
        """Return the fine body-part mask covered by currently worn components."""
        mask = BodyPart.NONE
        for component in self.components():
            if component.state != WearableState.ON:
                continue
            if component.layer < WearableLayer.INNER:
                continue
            for region in component.covers:
                mask |= region.to_part_mask()
        return mask

    def covered_regions(self) -> list[BodyRegion]:
        """Return coarse regions overlapped by currently worn components."""
        regions: set[BodyRegion] = set()
        for component in self.components():
            if component.state != WearableState.ON:
                continue
            if component.layer < WearableLayer.INNER:
                continue
            regions.update(component.covers)
        return sorted(regions, key=lambda region: region.name)

    def _validate_custom(self) -> list[str]:
        errors: list[str] = []

        uniform_count = sum(1 for comp in self.components() if comp.has_tags("uniform"))
        if 0 < uniform_count < 3:
            errors.append(f"Need 3+ uniform pieces (have {uniform_count})")

        for region in BodyRegion:
            items_here = [
                component for component in self.components() if region in component.covers
            ]
            items_here.sort(key=lambda wearable: wearable.layer.value)

            for idx, item in enumerate(items_here[:-1]):
                if item.state == WearableState.OPEN:
                    covering_item = items_here[idx + 1]
                    if covering_item.state == WearableState.ON:
                        errors.append(
                            f"{item.label} is open but covered by closed {covering_item.label}"
                        )

        return errors


__all__ = ["OutfitManager"]
