from tangl.journal.media import MediaFragment
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.story.fabula.world_loader import build_world_from_bundle
from tangl.vm import ResolutionPhase as P
from tangl.vm.frame import Frame


def _load_media_world(add_worlds_to_sys_path):
    world, _ = build_world_from_bundle("media_mvp")
    return world


def test_block_emits_media_fragment(add_worlds_to_sys_path):
    world = _load_media_world(add_worlds_to_sys_path)
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
