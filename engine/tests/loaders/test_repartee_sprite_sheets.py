"""The repartee demo, end to end: pack sheets, story posture, service payloads.

This is the integration witness for sprite sheets. It compiles repartee against
the spaceport pack, plays the world through the ServiceManager, and reads each
staged portrait the way a remote client would -- through the media payload the
REST layer builds. Every other test proves one side of a seam; this one proves
the pieces agree when they are actually connected.

It exercises all three sources of a clip: an authored loop in a location, the
contest's posture chosen from game state, and an authored outcome in an aftermath.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.journal.fragments import ChoiceFragment, MediaFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.persistence import PersistenceManagerFactory
from tangl.service.media import MediaContentProfile, MediaRenderProfile, media_fragment_to_payload
from tangl.service.service_manager import ServiceManager
from tangl.service.world_registry import (
    clear_discovered_world_registries,
    pop_manual_world,
    register_manual_world,
)
from tangl.service.response import DirectEdgeRequest
from tangl.story import World

WORLD_ROOT = Path(__file__).resolve().parents[3] / "worlds" / "repartee_loop"


@pytest.fixture
def spaceport_service():
    clear_discovered_world_registries()
    World.clear_instances()
    bundle = WorldBundle.load(WORLD_ROOT)
    bundle.manifest.media_dir = "media_spaceport"
    world = WorldCompiler().compile(bundle)
    register_manual_world(world)
    try:
        yield ServiceManager(PersistenceManagerFactory.native_in_mem()), world
    finally:
        pop_manual_world(world.label)
        World.clear_instances()
        clear_discovered_world_registries()


class Walk:
    def __init__(self, manager: ServiceManager, world: World) -> None:
        self.manager, self.world = manager, world
        self.user_id = manager.create_user().details["user_id"]
        self.envelope = manager.create_story(user_id=self.user_id, world_id=world.label)

    @property
    def ledger_id(self):
        return self.envelope.metadata["ledger_id"]

    def choose(self, text: str | None = None, *, first: bool = False) -> None:
        choices = [f for f in self.envelope.fragments if isinstance(f, ChoiceFragment)]
        choice = choices[0] if first else next(c for c in choices if c.text == text)
        self.envelope = self.manager.resolve_choice(
            user_id=self.user_id,
            ledger_id=self.ledger_id,
            request=DirectEdgeRequest(edge_id=choice.edge_id, payload=choice.activation_payload),
        )

    def portrait(self) -> dict:
        """The last portrait staged in this update, as the REST layer would send it."""

        portraits = [
            f for f in self.envelope.fragments
            if isinstance(f, MediaFragment) and f.media_role == "dialog_im"
        ]
        return media_fragment_to_payload(
            portraits[-1],
            render_profile=MediaRenderProfile(content_profile=MediaContentProfile.MEDIA_SERVER),
            world_id=self.world.label,
            world_media_root=self.world.resources.resource_path,
        )


def _staged(payload: dict) -> tuple[str, str | None, str | None, list[str]]:
    hints = payload.get("staging_hints") or {}
    sheets = [sheet["manifest"]["image"] for sheet in payload.get("sprite_sheets", [])]
    return payload["url"].rsplit("/", 1)[-1], hints.get("media_clip"), hints.get("media_timing"), sheets


def test_the_spaceport_demo_stages_every_clip_source_through_the_service(spaceport_service) -> None:
    walk = Walk(*spaceport_service)

    walk.choose("Step into the practice court")
    assert _staged(walk.portrait()) == ("clerk_sprite.png", "idle", "loop", ["clerk_sprite-4x1.png"])

    walk.choose("Step out onto the quay")
    walk.choose("Go to The Practice Yard")
    assert _staged(walk.portrait()) == ("worker_sprite.png", "idle", "loop", ["worker_sprite-4x1.png"])

    # Contest, from game state: the player holds the initiative, so the dockhand is on guard.
    walk.choose("Challenge the dockhand")
    assert _staged(walk.portrait()) == ("worker_sprite.png", "response", None, ["worker_sprite-4x1.png"])

    # Aftermath, authored: he won by parrying and keeps his guard up.
    walk.choose(first=True)
    assert _staged(walk.portrait()) == ("worker_sprite.png", "response", None, ["worker_sprite-4x1.png"])

    walk.choose("Step back into the yard")
    walk.choose("Return to the map")
    walk.choose("Go to The Salon Terrace")
    assert _staged(walk.portrait()) == ("master_sprite.png", "idle", "loop", ["master_sprite-4x1.png"])

    # Contest, from game state: the master holds the initiative, so he is attacking.
    walk.choose("Challenge the salon master")
    assert _staged(walk.portrait()) == ("master_sprite.png", "call", None, ["master_sprite-4x1.png"])


def test_the_sheet_travels_as_a_servable_url_beside_the_still(spaceport_service) -> None:
    walk = Walk(*spaceport_service)
    walk.choose("Step into the practice court")
    payload = walk.portrait()
    [sheet] = payload["sprite_sheets"]

    assert payload["content_format"] == sheet["content_format"] == "url"
    assert sheet["url"].endswith("/images/clerk_sprite-4x1.png")
    assert sheet["manifest"]["clips"] == [
        {"name": "idle", "first": 0, "last": 1, "direction": "forward"},
        {"name": "call", "first": 2, "last": 2, "direction": "forward"},
        {"name": "response", "first": 3, "last": 3, "direction": "forward"},
    ]
    # Every frame carries its own anchor: the export's one pivot key, resolved.
    assert {(f["pivot"]["x"], f["pivot"]["y"]) for f in sheet["manifest"]["frames"]} == {(51, 111)}


def test_the_default_quayside_pack_stages_the_same_clips_and_no_sheets() -> None:
    """The script asks for clips regardless of pack; a pack without sheets simply shows stills."""

    clear_discovered_world_registries()
    World.clear_instances()
    try:
        manager = ServiceManager(PersistenceManagerFactory.native_in_mem())
        world = WorldCompiler().compile(WorldBundle.load(WORLD_ROOT))
        register_manual_world(world)
        walk = Walk(manager, world)
        walk.choose("Step into the practice court")

        still, clip, timing, sheets = _staged(walk.portrait())
        assert (still, clip, timing, sheets) == ("clerk_sprite.png", "idle", "loop", [])
    finally:
        pop_manual_world("repartee_loop")
        World.clear_instances()
        clear_discovered_world_registries()
