from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from tangl.journal.fragments import ContentFragment, GroupFragment
from tangl.journal.media import MediaFragment
from tangl.media import story_media as story_media_mod
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media.media_resource import MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.controllers import runtime_controller as runtime_controller_mod
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.user.user import User
from tangl.story.story_graph import StoryGraph
from tangl.vm.runtime.ledger import Ledger
from tangl.vm.traversable import TraversableNode


def _rit_from_svg(tmp_path: Path, filename: str) -> MediaRIT:
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>',
        encoding="utf-8",
    )
    return MediaRIT(path=path, data_type=MediaDataType.IMAGE, label=filename)


def test_dereference_media_world_scope_uses_world_prefix(tmp_path: Path) -> None:
    rit = _rit_from_svg(tmp_path, "scene.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="world",
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/world/w1/scene.svg"
    assert payload["scope"] == "world"


def test_dereference_media_sys_scope_uses_sys_prefix(tmp_path: Path) -> None:
    rit = _rit_from_svg(tmp_path, "logo.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="sys",
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/sys/logo.svg"
    assert payload["scope"] == "sys"


def test_dereference_media_story_scope_uses_story_prefix_and_story_id(tmp_path: Path) -> None:
    rit = _rit_from_svg(tmp_path, "avatar.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="story",
        story_id="story-77",
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/story/story-77/avatar.svg"
    assert payload["scope"] == "story"


def test_dereference_media_story_scope_preserves_nested_subpath(monkeypatch, tmp_path: Path) -> None:
    story_root = tmp_path / "story_media"
    story_id = "story-77"
    rit = _rit_from_svg(story_root / story_id, "book1/scene1/avatar.svg")
    fragment = MediaFragment(
        content=rit,
        content_format="rit",
        content_type=MediaDataType.IMAGE,
        source_id=uuid4(),
        scope="story",
        story_id=story_id,
    )

    monkeypatch.setattr(
        runtime_controller_mod,
        "get_story_media_dir",
        lambda value=None: story_root if value is None else story_root / str(value),
    )

    payload = RuntimeController()._dereference_media(fragment, world_id="w1")

    assert payload["url"] == "/media/story/story-77/book1/scene1/avatar.svg"
    assert payload["scope"] == "story"


def test_get_story_update_serializes_media_journal_entries_with_nested_world_paths(tmp_path: Path) -> None:
    media_root = tmp_path / "world_media"
    rit = _rit_from_svg(media_root, "book1/scene1/cover.svg")

    graph = StoryGraph(
        label="story",
        world=SimpleNamespace(
            label="w1",
            resources=SimpleNamespace(resource_path=media_root),
        ),
    )
    node = TraversableNode(label="start")
    graph.add(node)
    ledger = Ledger(graph=graph, cursor_id=node.uid)
    ledger.output_stream.append(
        MediaFragment(
            content=rit,
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            source_id=node.uid,
            scope="world",
            step=0,
        )
    )

    info = RuntimeController().get_story_update(ledger=ledger)
    details = dict(info.details or {})
    envelope = details.get("envelope")

    assert isinstance(envelope, dict)
    fragments = envelope.get("fragments")
    assert isinstance(fragments, list)
    assert fragments[0]["fragment_type"] == "media"
    assert fragments[0]["url"] == "/media/world/w1/book1/scene1/cover.svg"


def test_get_story_update_preserves_richer_peer_fragments_without_service_rewrite() -> None:
    graph = StoryGraph(
        label="story",
        world=SimpleNamespace(
            label="w1",
            resources=SimpleNamespace(resource_path=None),
        ),
    )
    node = TraversableNode(label="start")
    graph.add(node)
    ledger = Ledger(graph=graph, cursor_id=node.uid)

    content = ContentFragment(content="Hello there", source_id=node.uid, step=0)
    overlay = GroupFragment(member_ids=[content.uid], group_type="summary", step=0)
    ledger.output_stream.append(content)
    ledger.output_stream.append(overlay)

    info = RuntimeController().get_story_update(ledger=ledger)
    details = dict(info.details or {})
    envelope = details.get("envelope")

    assert isinstance(envelope, dict)
    fragments = envelope.get("fragments")
    assert isinstance(fragments, list)
    assert [fragment["fragment_type"] for fragment in fragments] == ["content", "group"]
    assert fragments[1]["group_type"] == "summary"
    assert fragments[1]["member_ids"] == [str(content.uid)]


def test_get_journal_entries_applies_static_fallback_profile(tmp_path: Path) -> None:
    media_root = tmp_path / "world_media"
    resources = ResourceManager(resource_path=media_root, scope="world")
    fallback_rit = _rit_from_svg(media_root, "placeholder.svg")
    resources.registry.add(fallback_rit)

    graph = StoryGraph(
        label="story",
        world=SimpleNamespace(
            label="w1",
            resources=resources,
        ),
    )
    node = TraversableNode(label="start")
    graph.add(node)
    ledger = Ledger(graph=graph, cursor_id=node.uid)
    ledger.output_stream.append(
        MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.PENDING,
                adapted_spec_hash="pending-1",
                derivation_spec={"fallback_ref": "placeholder.svg"},
                data_type=MediaDataType.IMAGE,
            ),
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            source_id=node.uid,
            scope="world",
        )
    )

    fragments = RuntimeController().get_journal_entries(ledger=ledger)

    assert len(fragments) == 1
    assert fragments[0].fragment_type == "media"
    assert fragments[0].url == "/media/world/w1/placeholder.svg"


def test_get_journal_entries_omits_failed_media_without_fallback() -> None:
    graph = StoryGraph(
        label="story",
        world=SimpleNamespace(
            label="w1",
            resources=SimpleNamespace(resource_path=None),
        ),
    )
    node = TraversableNode(label="start")
    graph.add(node)
    ledger = Ledger(graph=graph, cursor_id=node.uid)
    ledger.output_stream.append(
        MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.FAILED,
                adapted_spec_hash="failed-1",
                data_type=MediaDataType.IMAGE,
            ),
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            source_id=node.uid,
            scope="story",
        )
    )

    fragments = RuntimeController().get_journal_entries(ledger=ledger)

    assert fragments == []


def test_get_story_update_omits_failed_media_without_fallback() -> None:
    graph = StoryGraph(
        label="story",
        world=SimpleNamespace(
            label="w1",
            resources=SimpleNamespace(resource_path=None),
        ),
    )
    node = TraversableNode(label="start")
    graph.add(node)
    ledger = Ledger(graph=graph, cursor_id=node.uid)
    ledger.output_stream.append(
        MediaFragment(
            content=MediaRIT(
                status=MediaRITStatus.FAILED,
                adapted_spec_hash="failed-2",
                data_type=MediaDataType.IMAGE,
            ),
            content_format="rit",
            content_type=MediaDataType.IMAGE,
            source_id=node.uid,
            scope="story",
        )
    )

    info = RuntimeController().get_story_update(ledger=ledger)
    details = dict(info.details or {})
    envelope = details.get("envelope")

    assert isinstance(envelope, dict)
    assert envelope.get("fragments") == []


def test_drop_story_removes_story_media_when_not_archived(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "story_media"
    story_dir = root / "story-1"
    story_dir.mkdir(parents=True)
    (story_dir / "asset.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

    monkeypatch.setattr(
        story_media_mod,
        "get_story_media_dir",
        lambda story_id=None: root if story_id is None else root / str(story_id),
    )

    user = User(label="runtime-user")
    user.current_ledger_id = "story-1"

    info = RuntimeController().drop_story(user=user, ledger=None, archive=False)

    assert info.details is not None
    assert info.details["story_media_deleted"] is True
    assert not story_dir.exists()


def test_drop_story_preserves_story_media_when_archived(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "story_media"
    story_dir = root / "story-2"
    story_dir.mkdir(parents=True)
    (story_dir / "asset.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

    monkeypatch.setattr(
        story_media_mod,
        "get_story_media_dir",
        lambda story_id=None: root if story_id is None else root / str(story_id),
    )

    user = User(label="runtime-user")
    user.current_ledger_id = "story-2"

    info = RuntimeController().drop_story(user=user, ledger=None, archive=True)

    assert info.details is not None
    assert "story_media_deleted" not in info.details
    assert story_dir.exists()
