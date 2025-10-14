from __future__ import annotations

from pathlib import Path

from tangl.core.dispatch import DispatchRegistry, HandlerPriority
from tangl.media import (
    MediaDataType,
    MediaResourceInventoryTag,
    MediaResourceRegistry,
)


def create_media_file(path: Path, name: str, content: bytes = b"pixels") -> Path:
    file_path = path / name
    file_path.write_bytes(content)
    return file_path


def test_discover_from_directory_indexes_media(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    backgrounds = assets_dir / "backgrounds"
    backgrounds.mkdir(parents=True)
    icons = assets_dir / "icons"
    icons.mkdir()

    forest = create_media_file(backgrounds, "forest-scene.png")
    create_media_file(icons, "select.mp3", b"sound")

    registry = MediaResourceRegistry()
    discovered = registry.discover_from_directory(assets_dir, role="world")

    assert len(discovered) == 2

    forest_entry = next(r for r in discovered if r.path == forest.resolve())
    assert forest_entry.media_type is MediaDataType.IMAGE
    assert forest_entry.role == "world"
    assert {"forest", "scene", "backgrounds"}.issubset(forest_entry.tags)

    match = registry.find_one(tags={"backgrounds", "forest"}, media_type=MediaDataType.IMAGE)
    assert match is forest_entry


def test_discover_skips_unknown_and_duplicates(tmp_path: Path) -> None:
    root = tmp_path / "world"
    root.mkdir()
    create_media_file(root, "readme.txt", b"hello")
    hero = create_media_file(root, "hero.png", b"hero")

    registry = MediaResourceRegistry()
    first_pass = registry.discover_from_directory(root)
    assert [rit.path for rit in first_pass] == [hero.resolve()]

    second_pass = registry.discover_from_directory(root)
    assert second_pass == []


def test_add_deduplicates_by_content_hash(tmp_path: Path) -> None:
    shared = b"same-data"
    file_a = create_media_file(tmp_path, "a.png", shared)
    file_b = create_media_file(tmp_path, "b.png", shared)

    registry = MediaResourceRegistry()
    rit_a = registry.add(MediaResourceInventoryTag.from_path(file_a))
    rit_b = registry.add(MediaResourceInventoryTag.from_path(file_b))

    assert rit_a is rit_b
    assert list(registry.find_all()) == [rit_a]


def test_custom_indexing_handlers_can_mutate_records(tmp_path: Path) -> None:
    calls: list[str] = []
    handlers = DispatchRegistry(label="test_indexers")

    @handlers.register(priority=HandlerPriority.NORMAL)
    def track_calls(ns: dict) -> None:  # pragma: no cover - callable exercised via registry
        rit = ns["rit"]
        rit.tags.add("processed")
        calls.append(rit.path.name)

    registry = MediaResourceRegistry(indexing_handlers=handlers)
    file_path = create_media_file(tmp_path, "landscape.png")

    rit = MediaResourceInventoryTag.from_path(file_path)
    registry.add(rit)

    assert "processed" in rit.tags
    assert calls == ["landscape.png"]

    other = MediaResourceInventoryTag.from_path(create_media_file(tmp_path, "other.png"))
    registry.add(other, run_handlers=False)

    assert "processed" not in other.tags


def test_find_by_tags_accepts_string_input(tmp_path: Path) -> None:
    file_path = create_media_file(tmp_path, "cave-entrance.png")
    registry = MediaResourceRegistry()
    registry.add(MediaResourceInventoryTag.from_path(file_path))

    results = list(registry.find_by_tags("cave"))
    assert results
    assert results[0].path.name == "cave-entrance.png"
