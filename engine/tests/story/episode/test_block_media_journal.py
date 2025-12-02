import pytest

from tangl.journal.media import MediaFragment
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.service.world_registry import WorldRegistry
from tangl.story.fabula.world import World
from tangl.vm import ResolutionPhase as P
from tangl.vm.frame import Frame


@pytest.fixture(autouse=True)
def clear_world_singleton():
    World.clear_instances()
    yield
    World.clear_instances()


def _load_media_world(media_mvp_path):
    registry = WorldRegistry([media_mvp_path.parent])
    return registry.get_world("media_mvp")


def test_block_emits_media_fragment(media_mvp_path):
    world = _load_media_world(media_mvp_path)
    story = world.create_story("Media MVP Story")
    block = story.get(story.initial_cursor_id)

    frame = Frame(graph=story, cursor_id=block.uid)
    frame.run_phase(P.PLANNING)

    fragments = frame.run_phase(P.JOURNAL)
    media_fragments = [frag for frag in fragments if isinstance(frag, MediaFragment)]

    assert media_fragments
    fragment = media_fragments[0]

    assert isinstance(fragment.content, MediaRIT)
    assert fragment.content_format == "rit"
    assert fragment.media_role is not None
    assert fragment.content.path.name == "test_image.svg"
