from pathlib import Path
from uuid import uuid4

from tangl.core import StreamRegistry
from tangl.journal.content import ContentFragment
from tangl.journal.media import MediaFragment
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.response import RuntimeInfo
from tangl.story.episode.block import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm.frame import Frame
from tangl.vm.ledger import Ledger


def test_dereference_media_fragment_to_url():
    asset_path = (
        Path(__file__).resolve().parents[4]
        / "engine"
        / "tests"
        / "resources"
        / "worlds"
        / "media_mvp"
        / "media"
        / "test_image.svg"
    )

    rit = MediaRIT(
        path=asset_path,
        data_type=MediaDataType.IMAGE,
        label="test_image.svg",
    )

    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        media_role="narrative_im",
        text="A fierce dragon",
        source_id=uuid4(),
    )

    controller = RuntimeController()
    result = controller._dereference_media(fragment, world_id="test_world")

    assert result["fragment_type"] == "media"
    assert result["url"] == "/media/world/test_world/test_image.svg"
    assert result["media_role"] == "narrative_im"
    assert result["media_type"] == MediaDataType.IMAGE.value
    assert result["text"] == "A fierce dragon"
    assert result["source_id"] == str(fragment.source_id)


def test_get_story_update_returns_runtime_info_with_fragments() -> None:
    class _WorldStub:
        def __init__(self, uid: str) -> None:
            self.uid = uid

        def unstructure(self) -> dict[str, str]:
            return {"uid": self.uid}

    graph = StoryGraph(label="media_story")
    start = graph.add_node(obj_cls=Block, label="start")
    graph.world = _WorldStub(uid="media_world")
    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    media_path = (
        Path(__file__).resolve().parents[4]
        / "engine"
        / "tests"
        / "resources"
        / "worlds"
        / "media_mvp"
        / "media"
        / "test_image.svg"
    )

    fragments = [
        ContentFragment(content="[step 0001]: cursor at start"),
        ContentFragment(content="Narration"),
        MediaFragment(
            content=MediaRIT(path=media_path, data_type=MediaDataType.IMAGE),
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            media_role="narrative_im",
            text="Illustration",
            source_id=uuid4(),
        ),
    ]

    ledger.records.push_records(*fragments, marker_type="journal", marker_name="step-0001")

    controller = RuntimeController()
    frame = Frame(graph=graph, cursor_id=start.uid)

    result = controller.get_story_update(ledger=ledger, frame=frame)

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert result.cursor_id == start.uid
    assert result.step == ledger.step

    payload = result.details or {}
    fragment_payloads = payload.get("fragments", [])

    assert fragment_payloads, "Expected dereferenced fragments in runtime update"
    assert any(frag.get("fragment_type") == "media" for frag in fragment_payloads)
    assert any(
        frag.get("url", "").endswith("/test_image.svg") for frag in fragment_payloads
    )
