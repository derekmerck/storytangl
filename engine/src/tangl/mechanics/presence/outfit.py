"""Outfit loadout surface for presence mechanics.

Why
---
`OutfitManager` is a real mechanics building block used by appearance-oriented
facets such as `look`. It belongs in the `presence` family rather than behind an
`assembly.examples` import path.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field, model_validator

from tangl.core import Entity, contribute_ns
from tangl.lang.helpers import oxford_join
from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.mechanics.presence.wearable import Wearable
from tangl.mechanics.presence.wearable.enums import WearableLayer, WearableState
from tangl.mechanics.transaction import (
    AssetMoveCommitment,
    ComponentAssignmentCommitment,
    ComponentSlotAssetHolder,
    ListAssetHolder,
    TransactionCommitment,
    TransactionOffer,
)


WARDROBE_SLOT = "stored"


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


class WardrobeManager(ComponentManager[Wearable]):
    """Owner-bound storage for wearable graph members not currently worn."""

    slots = {
        WARDROBE_SLOT: Slot.for_type(
            WARDROBE_SLOT,
            Wearable,
            max_count=1000,
        )
    }

    def holder(self) -> ComponentSlotAssetHolder:
        """Return the transaction holder view over stored wearables."""
        return ComponentSlotAssetHolder(self, WARDROBE_SLOT)

    def components(self) -> list[Wearable]:
        """Return a stable list of stored wearables."""
        result = list(self.get_slot(WARDROBE_SLOT))
        result.sort(
            key=lambda wearable: (
                wearable.label or "",
                wearable.noun or "",
            )
        )
        return result

    def describe_items(self) -> list[str]:
        """Return concise labels for stored wearables."""
        return [
            desc
            for component in self.components()
            if (desc := component.render_desc())
        ]

    def describe(self) -> str:
        """Return a compact phrase describing the current wardrobe."""
        return oxford_join(self.describe_items())


class HasWardrobe(Entity):
    """Direct facet exposing inactive wearable storage."""

    wardrobe: WardrobeManager = Field(
        default_factory=WardrobeManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_wardrobe_owner(self) -> "HasWardrobe":
        self.wardrobe.bind_owner(self)
        return self

    def describe_wardrobe(self) -> str:
        """Return a compact phrase describing stored wearables."""
        return self.wardrobe.describe()

    @contribute_ns
    def provide_wardrobe_symbols(self) -> dict[str, object]:
        """Publish direct wardrobe symbols into the entity-local namespace."""
        return {
            "wardrobe": self.wardrobe,
            "wardrobe_description": self.describe_wardrobe(),
            "wardrobe_tokens": self.wardrobe.describe_items(),
        }


def build_wardrobe_dress_offer(
    *,
    wardrobe: WardrobeManager,
    outfit: OutfitManager,
    wearable_key: str,
    slot_name: str,
    label: str | None = None,
    extra_commitments: Iterable[TransactionCommitment] = (),
) -> TransactionOffer:
    """Build a transaction that moves one stored wearable onto an outfit slot."""

    holder = wardrobe.holder()
    wearable = holder.get_asset(wearable_key)
    if wearable is None:
        raise ValueError(f"Wardrobe item not found: {wearable_key}")

    worn = ListAssetHolder([])
    commitments: list[TransactionCommitment] = [
        AssetMoveCommitment(
            holder,
            worn,
            wearable,
            label="remove selected wearable from wardrobe",
        ),
        ComponentAssignmentCommitment(
            outfit,
            slot_name,
            wearable,
            label="assign wearable to outfit",
            validate_after=True,
        ),
    ]
    commitments.extend(extra_commitments)
    return TransactionOffer(
        label=label or f"wear {wearable.get_label()}",
        commitments=commitments,
    )


__all__ = [
    "HasWardrobe",
    "OutfitManager",
    "WARDROBE_SLOT",
    "WardrobeManager",
    "build_wardrobe_dress_offer",
]
