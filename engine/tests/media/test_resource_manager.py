from __future__ import annotations

from pathlib import Path

from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.resource_manager import ResourceManager


def _write_svg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>',
        encoding="utf-8",
    )


def _write_blue_svg(path: Path) -> None:
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="blue"/></svg>',
        encoding="utf-8",
    )


def test_resource_manager_index_handlers_can_replace_records(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    svg_path = media_dir / "cover-hero-book1.svg"
    _write_svg(svg_path)

    def _retag(record: MediaRIT, *, ctx=None) -> MediaRIT:
        return record.model_copy(
            update={
                "label": "cover",
                "tags": {"hero", "book1"},
            }
        )

    resource_manager = ResourceManager(resource_path=media_dir, scope="world")
    resource_manager.register_index_handler(_retag)

    records = resource_manager.index_directory(".")

    assert len(records) == 1
    rit = resource_manager.get_rit("cover")
    assert rit is not None
    assert rit.path == svg_path
    assert {"hero", "book1", "scope:world"}.issubset(set(rit.tags or set()))


def test_resource_manager_registry_local_behaviors_handle_index_task(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    svg_path = media_dir / "road-arena-book2.svg"
    _write_svg(svg_path)

    def _retag(record: MediaRIT, *, ctx=None) -> MediaRIT:
        record.label = "road"
        record.tags |= {"arena", "book2"}
        return record

    resource_manager = ResourceManager(resource_path=media_dir, scope="world")
    resource_manager.registry.local_behaviors.register(task="index", func=_retag)

    records = resource_manager.index_directory(".")

    assert len(records) == 1
    rit = resource_manager.get_rit("road")
    assert rit is not None
    assert rit.path == svg_path
    assert {"arena", "book2", "scope:world"}.issubset(set(rit.tags or set()))


def test_media_registry_on_index_alias_registers_index_handler(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    svg_path = media_dir / "cover-hero-book3.svg"
    _write_svg(svg_path)

    def _retag(record: MediaRIT, *, ctx=None) -> MediaRIT:
        record.label = "cover"
        record.tags |= {"hero", "book3"}
        return record

    resource_manager = ResourceManager(resource_path=media_dir, scope="world")
    resource_manager.registry.on_index(_retag)

    records = resource_manager.index_directory(".")

    assert len(records) == 1
    rit = resource_manager.get_rit("cover")
    assert rit is not None
    assert rit.path == svg_path
    assert {"hero", "book3", "scope:world"}.issubset(set(rit.tags or set()))


def test_resource_manager_get_rit_skips_records_outside_resource_root(tmp_path: Path) -> None:
    resource_root = tmp_path / "media"
    images_dir = resource_root / "images"
    images_dir.mkdir(parents=True)
    inside_path = images_dir / "cover.svg"
    _write_svg(inside_path)

    outside_path = tmp_path / "outside.svg"
    _write_blue_svg(outside_path)

    resource_manager = ResourceManager(resource_path=resource_root, scope="world")
    resource_manager.registry.add(MediaRIT.from_source(outside_path))
    resource_manager.index_directory("images")

    rit = resource_manager.get_rit("images/cover.svg")
    assert rit is not None
    assert rit.path == inside_path


def test_resource_manager_indexes_nested_paths_recursively(tmp_path: Path) -> None:
    resource_root = tmp_path / "media"
    nested_path = resource_root / "book1" / "scene1" / "cover.svg"
    _write_svg(nested_path)

    resource_manager = ResourceManager(resource_path=resource_root, scope="world")
    records = resource_manager.index_directory(".")

    assert len(records) == 1
    rit = resource_manager.get_rit("book1/scene1/cover.svg")
    assert rit is not None
    assert rit.path == nested_path
