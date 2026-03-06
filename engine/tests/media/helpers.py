from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from tangl.media.media_resource.media_dependency import MediaDep
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.vm import Frame as VmFrame

if hasattr(VmFrame, "_make_ctx"):
    from tangl.story import Block, StoryGraph38 as StoryGraph
else:
    from tangl.story import Block, LegacyStoryGraph as StoryGraph


class MediaWorld(NamedTuple):
    world: object
    story: StoryGraph
    block: Block


class _SystemMediaWorld:
    def __init__(self, *, label: str, resource_manager: ResourceManager, story: StoryGraph) -> None:
        self.label = label
        self.uid = label
        self.resource_manager = resource_manager
        self._story = story

    def create_story(self) -> StoryGraph:
        self._story.world = self
        return self._story

    def unstructure(self) -> dict[str, str]:
        return {"label": self.label}

    def matches(self, **_: object) -> bool:
        return True


def _add_node(story: StoryGraph, *, kind, **attrs):
    try:
        return story.add_node(kind=kind, **attrs)
    except TypeError:
        return story.add_node(obj_cls=kind, **attrs)


def build_world_with_logo_media_block(world_media_dir: Path | None = None) -> MediaWorld:
    """Construct a minimal world containing a block with a ``logo.svg`` media dependency."""

    media_root = world_media_dir or Path(".")
    media_root.mkdir(parents=True, exist_ok=True)
    resource_manager = ResourceManager(media_root)
    resource_manager.index_directory(".")

    story = StoryGraph(label="system-media-story")
    block = _add_node(story, kind=Block, label="intro")
    story.initial_cursor_id = block.uid

    dep = MediaDep(
        graph=story,
        source_id=block.uid,
        media_path="logo.svg",
        media_role="logo",
    )
    if dep.registry is None:
        story.add(dep)

    world = _SystemMediaWorld(label="system_media_world", resource_manager=resource_manager, story=story)
    story.world = world

    return MediaWorld(world=world, story=story, block=block)
