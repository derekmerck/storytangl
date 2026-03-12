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
    Look,
    LookMediaPayload,
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


def _build_outfit(actor: HasLook) -> None:
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


def _build_ornaments(actor: HasLook) -> None:
    actor.ornamentation.add_ornament(
        Ornament(
            body_part=BodyPart.LEFT_ARM,
            ornament_type=OrnamentType.TATTOO,
            text="a dragon",
        )
    )


class DemoActor(StoryActor, HasLook):
    """Story actor used to exercise the look facet contract."""


class TestLookDescription:
    """Tests for deterministic appearance descriptions."""

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

    def test_default_facet_attachments_are_constructed_and_bound(self) -> None:
        actor = DemoActor(label="guide")

        assert actor.look is not None
        assert actor.outfit is not None
        assert actor.ornamentation is not None
        assert actor.outfit.owner is actor


class TestLookMediaPayload:
    """Tests for the structured media adapter payload."""

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
    """Tests for story-facing namespace publication."""

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
        assert namespace["apparent_gender"] == actor.look.apparent_gender
