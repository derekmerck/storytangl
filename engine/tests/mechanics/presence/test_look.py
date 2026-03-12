"""Tests for tangl.mechanics.presence.look.

Organized by functionality:
- description output: deterministic appearance phrasing
- media payloads: structured adapter artifacts
- facet composition: story actor namespace publication
"""

from __future__ import annotations

import pytest

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
from tangl.mechanics.presence.wearable import Wearable, WearableLayer, WearableType
from tangl.story.concepts import Actor as StoryActor


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
    )

    actor.outfit.assign("top_60", Wearable(label=shirt_type.label))
    actor.outfit.assign("top_80", Wearable(label=coat_type.label))


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
        assert "a dragon tattoo on their left arm" in description
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
        assert payload.ornament_tokens == ["a dragon tattoo on their left arm"]


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
