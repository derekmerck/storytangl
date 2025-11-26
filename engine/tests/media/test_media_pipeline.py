from __future__ import annotations

from pathlib import Path

import pytest
import itertools

from tangl.core.graph import Graph, Node
from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import (
    MediaDep,
    MediaProvisioner,
    MediaResourceInventoryTag as MediaRIT,
    MediaResourceRegistry,
)
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.story.episode.block import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import Context, Frame, ResolutionPhase as P
from tangl.vm.planning import MediaRequirement
from tangl.vm.provision import ProvisioningPolicy


@pytest.fixture()
def context_with_cursor() -> Context:
    graph = Graph()
    cursor = Node(graph=graph)
    return Context(graph=graph, cursor_id=cursor.uid, step=0)


def test_media_requirement_from_template() -> None:
    graph = Graph()
    requirement = MediaRequirement(
        graph=graph,
        template={"media_path": "tavern.png", "media_role": "narrative_im", "world_id": "demo"},
    )

    assert requirement.media_path == "tavern.png"
    assert requirement.media_role == "narrative_im"
    assert requirement.world_id == "demo"


def test_media_provisioner_offers_existing(context_with_cursor: Context, tmp_path: Path) -> None:
    registry = MediaResourceRegistry()
    existing_path = tmp_path / "demo.png"
    existing_path.write_bytes(b"demo")
    existing = MediaRIT(path=existing_path)
    registry.add(existing)

    requirement = MediaRequirement.for_path(graph=Graph(), media_path=str(existing_path))
    provisioner = MediaProvisioner(media_registry=registry)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=context_with_cursor))

    assert len(offers) == 1
    offer = offers[0]
    assert offer.operation is ProvisioningPolicy.EXISTING
    assert offer.provider_id == existing.uid
    assert offer.accept(ctx=context_with_cursor) is existing


def test_media_provisioner_creates_new_rit(context_with_cursor: Context, tmp_path: Path) -> None:
    registry = MediaResourceRegistry()
    new_path = tmp_path / "new.png"
    new_path.write_bytes(b"demo")
    requirement = MediaRequirement.for_path(graph=Graph(), media_path=str(new_path))
    provisioner = MediaProvisioner(media_registry=registry)

    offers = list(provisioner.get_dependency_offers(requirement, ctx=context_with_cursor))

    assert len(offers) == 1
    offer = offers[0]
    assert offer.operation is ProvisioningPolicy.CREATE
    provided = offer.accept(ctx=context_with_cursor)
    assert provided in registry
    assert Path(provided.path).name == "new.png"


def test_block_emits_media_fragment(tmp_path: Path) -> None:
    graph = StoryGraph()
    block = Block(graph=graph)
    block_path = tmp_path / "block.png"
    block_path.write_bytes(b"demo")
    rit = MediaRIT(path=block_path, graph=graph)
    requirement = MediaRequirement.for_path(graph=graph, media_path=str(block_path))
    requirement.provider = rit
    MediaDep(graph=graph, source_id=block.uid, destination_id=rit.uid, requirement=requirement)

    frame = Frame(graph=graph, cursor_id=block.uid)
    handler_fragments = block.emit_media_fragments(ctx=frame.context)

    assert handler_fragments is not None
    fragment = handler_fragments[0]
    assert fragment.content is rit
    assert fragment.media_role == requirement.media_role


def test_runtime_controller_dereferences_media(tmp_path: Path) -> None:
    controller = RuntimeController()
    story_path = tmp_path / "story.png"
    story_path.write_bytes(b"demo")
    rit = MediaRIT(path=story_path)
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        media_role="narrative_im",
        content_type=MediaDataType.IMAGE,
        source_id=None,
    )

    payload = controller._dereference_media_fragment(  # pylint: disable=protected-access
        fragment=fragment,
        world_id="demo",
    )

    assert payload["url"].endswith("/demo/story.png")
    assert payload["fragment_type"] == "media"
