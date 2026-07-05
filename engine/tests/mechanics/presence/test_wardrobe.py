"""Tests for presence wardrobe loadouts.

Organized by functionality:
- storage: owner-bound inactive wearable storage
- dressing: transaction-backed moves from wardrobe to active outfit
- serialization: graph round-trips preserve wearable graph identity
"""

from __future__ import annotations

import pytest

from tangl.core import Graph, Selector
from tangl.lang.body_parts import BodyRegion
from tangl.mechanics.presence.outfit import (
    HasWardrobe,
    WARDROBE_SLOT,
    build_wardrobe_dress_offer,
)
from tangl.mechanics.presence.look import HasOutfit
from tangl.mechanics.presence.wearable import (
    Wearable,
    WearableLayer,
    WearableState,
    WearableType,
)
from tangl.story.concepts import Actor as StoryActor


@pytest.fixture(autouse=True)
def reset_wearable_types():
    WearableType.clear_instances()
    yield
    WearableType.clear_instances()


class WardrobeActor(StoryActor, HasOutfit, HasWardrobe):
    """Story actor with both inactive wardrobe storage and an active outfit."""


def wearable_type(
    label: str,
    noun: str,
    *,
    region: BodyRegion = BodyRegion.TOP,
    layer: WearableLayer = WearableLayer.OUTER,
    tags: set[str] | None = None,
) -> WearableType:
    return WearableType(
        label=label,
        noun=noun,
        covers={region},
        layer=layer,
        tags=tags or set(),
    )


class TestWardrobeStorage:
    """Tests for owner-bound wardrobe storage."""

    def test_wardrobe_publishes_namespace_symbols(self) -> None:
        shirt_type = wearable_type("wardrobe_symbol_shirt", "shirt")
        actor = WardrobeActor(label="guide")
        shirt = Wearable(
            label="guide-shirt",
            token_from=shirt_type.label,
        )

        actor.wardrobe.assign(WARDROBE_SLOT, shirt)
        namespace = actor.get_ns()

        assert actor.wardrobe.owner is actor
        assert namespace["wardrobe"] is actor.wardrobe
        assert namespace["wardrobe_description"] == "shirt"
        assert namespace["wardrobe_tokens"] == ["shirt"]

    def test_graph_roundtrip_preserves_wardrobe_and_outfit_assignments_by_id(self) -> None:
        shirt_type = wearable_type("wardrobe_roundtrip_shirt", "shirt")
        coat_type = wearable_type(
            "wardrobe_roundtrip_coat",
            "coat",
            layer=WearableLayer.OVER,
        )
        graph = Graph()
        actor = graph.add_node(kind=WardrobeActor, label="guide")
        shirt = graph.add_node(
            kind=Wearable,
            label="guide-shirt",
            token_from=shirt_type.label,
        )
        coat = graph.add_node(
            kind=Wearable,
            label="guide-coat",
            token_from=coat_type.label,
        )

        actor.wardrobe.assign(WARDROBE_SLOT, shirt)
        actor.outfit.assign("top_80", coat)

        actor_data = actor.unstructure()
        restored = Graph.structure(graph.unstructure())
        restored_actor = restored.find_one(Selector(label="guide"))
        restored_shirt = restored.find_one(Selector(label="guide-shirt"))
        restored_coat = restored.find_one(Selector(label="guide-coat"))

        assert actor_data["wardrobe"]["assignment_ids"] == {
            WARDROBE_SLOT: [shirt.uid],
        }
        assert actor_data["outfit"]["assignment_ids"] == {
            "top_80": [coat.uid],
        }
        assert restored_actor.wardrobe.owner is restored_actor
        assert restored_actor.outfit.owner is restored_actor
        assert restored_actor.wardrobe.get_slot(WARDROBE_SLOT) == [restored_shirt]
        assert restored_actor.outfit.get_slot("top_80") == [restored_coat]
        assert sum(1 for item in restored.members.values() if item.uid == shirt.uid) == 1
        assert sum(1 for item in restored.members.values() if item.uid == coat.uid) == 1


class TestWardrobeDressing:
    """Tests for transaction-backed dressing from wardrobe storage."""

    def test_dress_offer_moves_wearable_from_wardrobe_to_outfit(self) -> None:
        shirt_type = wearable_type("wardrobe_dress_shirt", "shirt")
        graph = Graph()
        actor = graph.add_node(kind=WardrobeActor, label="guide")
        shirt = graph.add_node(
            kind=Wearable,
            label="guide-shirt",
            token_from=shirt_type.label,
        )
        actor.wardrobe.assign(WARDROBE_SLOT, shirt)

        offer = build_wardrobe_dress_offer(
            wardrobe=actor.wardrobe,
            outfit=actor.outfit,
            wearable_key="guide-shirt",
            slot_name="top_60",
        )

        assert offer.can_accept().accepted
        receipt = offer.accept()

        assert receipt.offer_label == "wear guide-shirt"
        assert actor.wardrobe.get_slot(WARDROBE_SLOT) == []
        assert actor.outfit.get_slot("top_60") == [shirt]
        assert actor.describe_outfit() == "shirt"

    def test_dress_offer_rejects_slot_incompatible_wearable(self) -> None:
        pants_type = wearable_type(
            "wardrobe_dress_pants",
            "pants",
            region=BodyRegion.BOTTOM,
        )
        actor = WardrobeActor(label="guide")
        pants = Wearable(
            label="guide-pants",
            token_from=pants_type.label,
        )
        actor.wardrobe.assign(WARDROBE_SLOT, pants)

        offer = build_wardrobe_dress_offer(
            wardrobe=actor.wardrobe,
            outfit=actor.outfit,
            wearable_key="guide-pants",
            slot_name="top_60",
        )

        check = offer.can_accept()

        assert not check.accepted
        assert "Component doesn't match criteria" in (check.reason or "")
        assert actor.wardrobe.get_slot(WARDROBE_SLOT) == [pants]
        assert actor.outfit.get_slot("top_60") == []

    def test_dress_offer_rolls_back_wardrobe_move_when_outfit_validation_fails(
        self,
    ) -> None:
        shirt_type = wearable_type(
            "wardrobe_open_shirt",
            "shirt",
            layer=WearableLayer.INNER,
        )
        coat_type = wearable_type("wardrobe_closed_coat", "coat")
        actor = WardrobeActor(label="guide")
        coat = Wearable(label="guide-coat", token_from=coat_type.label)
        shirt = Wearable(
            label="guide-shirt",
            token_from=shirt_type.label,
            state=WearableState.OPEN,
        )
        actor.outfit.assign("top_60", coat)
        actor.wardrobe.assign(WARDROBE_SLOT, shirt)

        offer = build_wardrobe_dress_offer(
            wardrobe=actor.wardrobe,
            outfit=actor.outfit,
            wearable_key="guide-shirt",
            slot_name="top_40",
        )

        assert offer.can_accept().accepted
        with pytest.raises(ValueError, match="open but covered"):
            offer.accept()

        assert actor.wardrobe.get_slot(WARDROBE_SLOT) == [shirt]
        assert actor.outfit.get_slot("top_40") == []
        assert actor.outfit.get_slot("top_60") == [coat]
