"""Public world-info projection witness for the Ren'Py demo."""

from __future__ import annotations

from pathlib import Path

from tangl.core import Ctx
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.presentation.projection import BrandingValue, ProjectionRequest, TableValue
from tangl.service.dispatch import do_advertise_info_channels, do_get_world_info


def test_renpy_demo_publishes_cacheable_style_and_branding_channels() -> None:
    root = Path(__file__).resolve().parents[3] / "worlds" / "renpy_demo"
    world = WorldCompiler().compile(WorldBundle.load(root))
    ctx = Ctx(registries=tuple(world.get_authorities()))

    channels = do_advertise_info_channels(world, ctx=ctx)
    assert [channel.channel_id for channel in channels] == [
        "ui-style-hints-html",
        "ui-branding",
    ]

    branding = do_get_world_info(
        world,
        ctx=ctx,
        request=ProjectionRequest(channels=["ui-branding"]),
    ).sections[0].value
    assert isinstance(branding, BrandingValue)
    assert branding.logo_media == "guide_portrait.svg"
    assert branding.light is not None and branding.light.primary == "#6b4f8a"
    assert branding.dark is not None and branding.dark.primary == "#c8a9e8"

    styles = do_get_world_info(
        world,
        ctx=ctx,
        request=ProjectionRequest(channels=["ui-style-hints-html"]),
    ).sections[0].value
    assert isinstance(styles, TableValue)
    assert [row[0] for row in styles.rows] == [
        "st-emphasis",
        "st-emphasis--warn",
        "st-unavailable",
    ]
