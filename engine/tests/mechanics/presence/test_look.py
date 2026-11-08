"""Tests for tangl.mechanics.presence.look.

Organized by functionality:
- description output: deterministic appearance phrasing
- media payloads: structured adapter artifacts
- facet composition: story actor namespace publication
"""

from __future__ import annotations

import pytest

from tangl.core import Graph, Selector
from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.presence.look import (
    BodyPhenotype,
    EyeColor,
    HairColor,
    HairStyle,
    HasOrnamentation,
    HasOutfit,
    HasSimpleLook,
    Look,
    LookMediaPayload,
    OrnamentMediaPayload,
    OutfitMediaPayload,
    SkinTone,
)
from tangl.mechanics.presence.look.look import HasLook
from tangl.mechanics.presence.ornaments import Ornament, OrnamentType
from tangl.mechanics.presence.wearable import Wearable, WearableLayer, WearableState, WearableType
from tangl.story.concepts import Actor as StoryActor
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.structuring import StructuringHandler


@pytest.fixture(autouse=True)
def reset_wearable_types():
    WearableType.clear_instances()
    yield
    WearableType.clear_instances()


def _build_outfit(actor: HasOutfit | HasLook) -> None:
    shirt_type = WearableType(
        label="look_shirt",
        noun="shirt",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OUTER,
    )
    coat_type = WearableType(
        label="look_coat",
        noun="coat",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OVER,
        color="blue",
    )

    actor.outfit.assign("top_60", Wearable(token_from=shirt_type.label))
    actor.outfit.assign("top_80", Wearable(token_from=coat_type.label))


def _build_ornaments(actor: HasOrnamentation | HasLook) -> None:
    actor.ornamentation.add_ornament(
        Ornament(
            body_part=BodyPart.LEFT_ARM,
            ornament_type=OrnamentType.TATTOO,
            text="a dragon",
        )
    )


class DemoLookOnlyActor(StoryActor, HasSimpleLook):
    """Story actor used to exercise the direct look facet."""


class DemoOutfitActor(StoryActor, HasOutfit):
    """Story actor used to exercise the direct outfit facet."""


class DemoOrnamentActor(StoryActor, HasOrnamentation):
    """Story actor used to exercise the direct ornament facet."""


class DemoActor(StoryActor, HasLook):
    """Story actor used to exercise the look facet contract."""


class HornedLook(Look):
    horns: str = "curved"

    def trait_tokens(self) -> list[str]:
        return [*super().trait_tokens(), f"{self.horns} horns"]

    def media_traits(self) -> dict:
        return {**super().media_traits(), "horns": self.horns}


class TestDirectPresenceFacets:
    """Tests for the direct visual subfacets."""

    def test_direct_look_facet_publishes_only_look_symbols(self) -> None:
        actor = DemoLookOnlyActor(
            label="guide",
            look=Look(
                hair_color=HairColor.AUBURN,
                hair_style=HairStyle.BRAID,
                eye_color=EyeColor.GRAY,
            ),
        )

        namespace = actor.get_ns()

        assert namespace["look"] is actor.look
        assert "gray eyes" in namespace["look_description"]
        assert "auburn braid hair" in namespace["look_description"]
        assert namespace["look_media_payload"].traits["hair_color"] == "auburn"
        assert namespace["look_media_payload"].outfit_tokens == []
        assert "outfit" not in namespace
        assert "ornamentation" not in namespace

    def test_direct_outfit_facet_publishes_namespace_and_payload(self) -> None:
        actor = DemoOutfitActor(label="guide")
        _build_outfit(actor)

        namespace = actor.get_ns()
        payload = actor.adapt_outfit_media_spec(media_role="avatar_im")

        assert actor.outfit.owner is actor
        assert namespace["outfit"] is actor.outfit
        assert namespace["outfit_description"] == "shirt and coat"
        assert namespace["outfit_tokens"] == ["shirt", "coat"]
        assert isinstance(payload, OutfitMediaPayload)
        assert payload.description == "shirt and coat"
        assert payload.items == ["shirt", "coat"]
        assert payload.media_role == "avatar_im"

    def test_direct_ornament_facet_publishes_namespace_and_payload(self) -> None:
        actor = DemoOrnamentActor(label="guide")
        _build_ornaments(actor)

        namespace = actor.get_ns()
        payload = actor.adapt_ornament_media_spec(media_role="avatar_im")

        assert namespace["ornamentation"] is actor.ornamentation
        assert namespace["ornament_tokens"] == ["a dragon tattoo on their left arm"]
        assert namespace["ornament_description"] == "a dragon tattoo on their left arm"
        assert isinstance(payload, OrnamentMediaPayload)
        assert payload.description == "a dragon tattoo on their left arm"
        assert payload.items == ["a dragon tattoo on their left arm"]
        assert payload.media_role == "avatar_im"


class TestOutfitSerialization:
    """Graph-backed outfit manager persistence contract."""

    def test_actor_look_subtype_and_outfit_survive_json(self) -> None:
        graph = Graph()
        actor = graph.add_node(kind=DemoActor, label="guide", look=HornedLook(horns="spiral"))
        _build_outfit(actor)
        _build_ornaments(actor)
        mark = actor.ornamentation.collection[0]
        assert actor.ornamentation.uid not in graph.members
        assert mark.uid not in graph.members
        graph_before = graph.unstructure()
        hashes_before = {uid: item.value_hash() for uid, item in graph.members.items()}
        before = actor.adapt_look_media_spec()
        assert "spiral horns" in actor.describe_look()
        assert before.traits["horns"] == "spiral"
        actor.get_ns()
        assert graph.unstructure() == graph_before
        assert {uid: item.value_hash() for uid, item in graph.members.items()} == hashes_before
        direct = Graph.structure(graph_before)
        assert direct.get(actor.uid).adapt_look_media_spec() == before
        data = Json.deserialize(Json.serialize(graph_before))
        restored = StructuringHandler.structure(
            data, kind_map={cls.__fqn__(): cls for cls in (Graph, DemoActor, HornedLook)}
        )
        restored_actor = restored.get(actor.uid)
        assert isinstance(restored_actor.look, HornedLook)
        restored_mark = restored_actor.ornamentation.collection[0]
        assert type(restored_mark) is type(mark)
        assert (restored_mark.uid, restored_mark.body_part, restored_mark.ornament_type,
                restored_mark.text) == (mark.uid, mark.body_part, mark.ornament_type, mark.text)
        assert restored_actor.ornamentation.uid == actor.ornamentation.uid
        assert restored_actor.ornamentation.uid not in restored.members
        assert restored_mark.uid not in restored.members
        assert restored_actor.adapt_look_media_spec() == before
        for wearable in restored_actor.outfit.components():
            wearable.state = WearableState.OPEN
        restored_before = restored.unstructure()
        restored_hashes = {uid: item.value_hash() for uid, item in restored.members.items()}
        assert "dragon" in restored_actor.describe_look()
        assert "dragon" in " ".join(restored_actor.adapt_look_media_spec().ornament_tokens)
        assert "dragon" in " ".join(restored_actor.get_ns()["ornament_tokens"])
        assert restored.unstructure() == restored_before
        assert {uid: item.value_hash() for uid, item in restored.members.items()} == restored_hashes

    def test_graph_roundtrip_preserves_outfit_assignments_by_graph_id(self) -> None:
        shirt_type = WearableType(
            label="roundtrip_shirt",
            noun="shirt",
            covers={BodyRegion.TOP},
            layer=WearableLayer.OUTER,
        )
        coat_type = WearableType(
            label="roundtrip_coat",
            noun="coat",
            covers={BodyRegion.TOP},
            layer=WearableLayer.OVER,
        )
        graph = Graph()
        actor = graph.add_node(kind=DemoOutfitActor, label="guide")
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

        actor.outfit.assign("top_60", shirt)
        actor.outfit.assign("top_80", coat)

        actor_data = actor.unstructure()
        graph_data = graph.unstructure()
        restored = Graph.structure(graph_data)
        restored_actor = restored.find_one(Selector(label="guide"))
        restored_shirt = restored.find_one(Selector(label="guide-shirt"))
        restored_coat = restored.find_one(Selector(label="guide-coat"))

        assert {name: actor.outfit.slot_wallet(name).member_ids for name in actor_data["outfit"]["slot_wallet_ids"]} == {
            "top_60": [shirt.uid],
            "top_80": [coat.uid],
        }
        assert restored_actor.outfit.owner is restored_actor
        assert restored_actor.outfit.get_slot("top_60") == [restored_shirt]
        assert restored_actor.outfit.get_slot("top_80") == [restored_coat]
        assert restored_actor.outfit.describe_items() == ["shirt", "coat"]
        assert sum(1 for item in restored.members.values() if item.uid == shirt.uid) == 1
        assert sum(1 for item in restored.members.values() if item.uid == coat.uid) == 1


class TestLookDescription:
    """Tests for deterministic bundled appearance descriptions."""

    def test_describe_combines_traits_outfit_and_ornaments(self) -> None:
        actor = DemoActor(
            label="guide",
            look=Look(
                hair_color=HairColor.RED,
                hair_style=HairStyle.LONG,
                eye_color=EyeColor.GREEN,
                skin_tone=SkinTone.OLIVE,
                body_phenotype=BodyPhenotype.FIT,
            ),
        )
        _build_outfit(actor)
        _build_ornaments(actor)

        description = actor.describe_look(attitude="calm")

        assert "olive skin" in description
        assert "green eyes" in description
        assert "red long hair" in description
        assert "fit build" in description
        assert "wearing shirt and coat" in description
        assert "a dragon tattoo on their left arm" not in description
        assert "calm demeanor" in description

    def test_default_bundle_attachments_are_constructed_and_bound(self) -> None:
        actor = DemoActor(label="guide")

        assert actor.look is not None
        assert actor.outfit is not None
        assert actor.ornamentation is not None
        assert actor.outfit.owner is actor


class TestLookMediaPayload:
    """Tests for the structured bundled media adapter payload."""

    def test_adapt_media_spec_returns_structured_payload(self) -> None:
        actor = DemoActor(
            label="guide",
            look=Look(
                hair_color=HairColor.BLONDE,
                hair_style=HairStyle.BOB,
                eye_color=EyeColor.BLUE,
                skin_tone=SkinTone.LIGHT,
            ),
        )
        _build_outfit(actor)
        _build_ornaments(actor)

        payload = actor.adapt_look_media_spec(
            media_role="avatar_im",
            attitude="confident",
            pose="heroic",
        )

        assert isinstance(payload, LookMediaPayload)
        assert payload.media_role == "avatar_im"
        assert payload.attitude == "confident"
        assert payload.pose == "heroic"
        assert payload.traits["hair_color"] == "blonde"
        assert payload.traits["hair_style"] == "bob"
        assert payload.traits["eye_color"] == "blue"
        assert payload.traits["skin_tone"] == "light"
        assert payload.outfit_tokens == ["shirt", "coat"]
        assert payload.ornament_tokens == []

    def test_outfit_coverage_and_wearable_identity_are_consistent(self) -> None:
        actor = DemoActor(label="guide")
        _build_outfit(actor)
        _build_ornaments(actor)
        actor.ornamentation.add_ornament(
            Ornament(body_part=BodyPart.FACE, ornament_type=OrnamentType.MARKER, text="a crescent")
        )
        shirt, coat = actor.outfit.components()
        shirt.state = WearableState.OPEN
        for state, visible in ((WearableState.ON, False), (WearableState.OPEN, True),
                               (WearableState.OFF, True)):
            coat.state = state
            payload = actor.adapt_look_media_spec()
            namespace = actor.get_ns()
            assert ("dragon" in actor.describe_look()) is visible
            assert ("dragon" in " ".join(payload.ornament_tokens)) is visible
            assert ("dragon" in " ".join(namespace["ornament_tokens"])) is visible
            assert "crescent" in payload.description
            assert [item.instance_id for item in payload.wearables] == [shirt.uid, coat.uid]
            assert payload.wearables[1].type_label == coat.token_from
            assert payload.wearables[1].type_kind is WearableType
            assert payload.wearables[1].state == state
            assert payload.wearables[1].color == "blue"
            assert payload.wearables[1].covers == {BodyRegion.TOP}
            assert payload.wearables[1].layer == WearableLayer.OVER
            assert ("coat" in payload.outfit_tokens) is (state != WearableState.OFF)


class TestHasLookNamespace:
    """Tests for story-facing namespace publication through the bundle."""

    def test_story_actor_namespace_includes_look_symbols(self) -> None:
        actor = DemoActor(
            label="guide",
            look=Look(
                hair_color=HairColor.AUBURN,
                hair_style=HairStyle.BRAID,
                eye_color=EyeColor.GRAY,
            ),
        )
        _build_outfit(actor)

        namespace = actor.get_ns()

        assert namespace["look"] is actor.look
        assert namespace["outfit"] is actor.outfit
        assert namespace["look_media_payload"].traits["hair_color"] == "auburn"
        assert "wearing shirt and coat" in namespace["look_description"]
        assert namespace["outfit_description"] == "shirt and coat"
        assert namespace["outfit_tokens"] == ["shirt", "coat"]
        assert namespace["outfit_media_payload"].items == ["shirt", "coat"]
        assert namespace["ornament_tokens"] == []
        assert namespace["ornament_media_payload"].items == []
        assert namespace["apparent_gender"] == actor.look.apparent_gender
