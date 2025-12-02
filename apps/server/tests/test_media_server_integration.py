from __future__ import annotations

from pathlib import Path

from pathlib import Path

from fastapi.testclient import TestClient

from tangl.journal.media import MediaFragment
from tangl.rest import media_server
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.story.episode.block import Block
from tangl.story.fabula.world_loader import WorldLoader
from tangl.vm import ResolutionPhase as P
from tangl.vm.context import Context
from tangl.vm.frame import Frame


WORLD_ROOT = Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "worlds"


def test_media_story_round_trip(client: TestClient) -> None:  # noqa: PT004
    loader = WorldLoader([WORLD_ROOT])
    bundles = loader.discover_bundles()
    bundle = bundles["media_e2e"]
    world = loader.load_world("media_e2e")

    story = world.create_story("Media E2E Story")
    block = next(node for node in story.values() if isinstance(node, Block))

    frame = Frame(graph=story, cursor_id=block.uid)
    ctx = Context(graph=story, cursor_id=block.uid)
    frame.context = ctx
    frame.run_phase(P.PLANNING)

    fragments = frame.run_phase(P.JOURNAL)
    media_frag = next(frag for frag in fragments if isinstance(frag, MediaFragment))

    controller = RuntimeController()
    deref = controller._dereference_media(media_frag, world_id=world.label)
    media_url = deref["url"]

    media_server.mount_world_media(media_server.app, bundle.manifest.label, bundle.media_dir)

    response = client.get(f"http://test{media_url}")

    assert response.status_code == 200
    assert response.content
    assert response.headers["content-type"].startswith("image/")
