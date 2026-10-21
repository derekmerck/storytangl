from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from tangl.media import MediaDataType
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


def test_register_file_resolves_relative_paths_against_resource_root(tmp_path: Path) -> None:
    resource_root = tmp_path / "media"
    nested_path = resource_root / "book1" / "scene1" / "cover.svg"
    _write_svg(nested_path)

    resource_manager = ResourceManager(resource_path=resource_root, scope="world")
    rit = resource_manager.register_file(Path("book1/scene1/cover.svg"))

    assert rit.path == nested_path.resolve()
    assert resource_manager.get_rit("book1/scene1/cover.svg") is rit


def _path_record(*, label: str, path: Path | None = None) -> MediaRIT:
    """Declared bytes identity isolates lexical lookup from content loading."""
    return MediaRIT(label=label, path=path, content_hash=label.encode(),
                    data_type=MediaDataType.VECTOR)


def test_repeated_aliases_derive_each_path_root_pair_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = ResourceManager(tmp_path / "media")
    paths = [manager.resource_path / "nested" / f"{i}.svg" for i in range(4)]
    paths.append(tmp_path / "outside.svg")
    for i, path in enumerate(paths):
        manager.registry.add(_path_record(label=f"record_{i}", path=path))
    manager.registry.add(_path_record(label="pathless"))
    calls: list[tuple[Path, Path]] = []
    original = Path.relative_to

    def counted(path: Path, root: Path) -> Path:
        calls.append((path, root))
        return original(path, root)

    monkeypatch.setattr(Path, "relative_to", counted)
    for _ in range(3):
        assert manager.get_rit("missing") is None
        assert manager.get_rit("nested/3.svg").path == paths[3]
    assert calls == [(path, manager.resource_path) for path in paths]
    # Reusing immutable values is not a UID cache; two records can share a path.
    manager.registry.add(_path_record(label="same_path", path=paths[0]))
    assert manager.get_rit("missing") is None
    assert len(calls) == len(paths)
    manager.resource_path = tmp_path
    assert manager.get_rit("missing") is None
    assert calls[len(paths):] == [(path, tmp_path) for path in paths]


def test_label_identifier_and_ordered_basename_or_relative_precedence(tmp_path: Path) -> None:
    manager = ResourceManager(tmp_path)
    path_match = _path_record(label="path_record", path=tmp_path / "nested" / "picture.svg")
    manager.registry.add(path_match)
    identifier = _path_record(label="id_record")
    manager.registry.add(identifier)
    identifier_path = _path_record(label="id_path", path=tmp_path / identifier.shortcode())
    manager.registry.add(identifier_path)
    assert manager.get_rit(identifier.shortcode()) is identifier
    exact_label = _path_record(label=identifier.shortcode(), path=tmp_path / "other.svg")
    manager.registry.add(exact_label)
    assert manager.get_rit(identifier.shortcode()) is exact_label
    assert manager.get_rit("nested/picture.svg") is path_match
    labelled = _path_record(label="nested/picture.svg")
    manager.registry.add(labelled)
    assert manager.get_rit("nested/picture.svg") is labelled
    manager.registry.remove(labelled.uid)
    assert manager.get_rit("nested/picture.svg") is path_match

    # The earlier basename must beat a later root-relative match, and vice versa.
    early = _path_record(label="early", path=tmp_path / "elsewhere" / "picture.svg")
    later = _path_record(label="later", path=tmp_path / "picture.svg")
    manager.registry.clear()
    manager.registry.add(early)
    manager.registry.add(later)
    assert manager.get_rit("picture.svg") is early
    manager.registry.remove(early.uid)
    assert manager.get_rit("picture.svg") is later
    manager.registry.add(early)
    assert manager.get_rit("picture.svg") is later


@pytest.mark.parametrize("root,path,alias,found", [
    ("media", "media/nested/a.svg", "nested/a.svg", True),
    ("/media", "/media/nested/a.svg", "nested/a.svg", True),
    ("media", "media/../outside.svg", "../outside.svg", True),
    ("/media", "/outside/a.svg", "outside/a.svg", False),
    ("media", "/media/a.svg", "a.svg", True),  # basename works across root kinds
    ("media", "/media/nested/a.svg", "nested/a.svg", False),
    ("/media", "media/nested/a.svg", "nested/a.svg", False),
    ("/media", "/outside/a.svg", "a.svg", True),  # out-of-root basename stays legal
    ("/media", None, "missing", False),
])
def test_lookup_keeps_lexical_paths_and_does_not_touch_filesystem(
    root: str, path: str | None, alias: str, found: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = ResourceManager(Path(root))
    record = _path_record(label="not_an_alias", path=Path(path) if path is not None else None)
    manager.registry.add(record)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("lookup must not resolve or stat paths")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "resolve", forbidden)
        patch.setattr(Path, "stat", forbidden)
        for _ in range(2):
            assert manager.get_rit(alias) is (record if found else None)


def test_live_membership_overwrite_clear_and_direct_path_label_root_mutation(
    tmp_path: Path,
) -> None:
    manager = ResourceManager(tmp_path / "media")
    assert manager.get_rit("nested/a.svg") is None
    original = _path_record(label="original", path=manager.resource_path / "nested/a.svg")
    manager.registry.add(original)
    assert manager.get_rit("nested/a.svg") is original
    replacement = MediaRIT(uid=original.uid, label="replacement", path=original.path,
                           content_hash=b"replacement")
    manager.registry.add(replacement)
    assert manager.get_rit("nested/a.svg") is replacement
    replacement.path = manager.resource_path / "nested/b.svg"
    assert manager.get_rit("nested/a.svg") is None
    assert manager.get_rit("nested/b.svg") is replacement
    replacement.label = "nested/a.svg"
    assert manager.get_rit("nested/a.svg") is replacement
    replacement.label = "new_label"
    assert manager.get_rit("nested/a.svg") is None
    assert manager.get_rit("new_label") is replacement
    manager.resource_path = tmp_path
    assert manager.get_rit("nested/b.svg") is None
    assert manager.get_rit("media/nested/b.svg") is replacement
    manager.registry.remove(replacement.uid)
    assert manager.get_rit("media/nested/b.svg") is None
    manager.registry.add(original)
    assert manager.get_rit("media/nested/a.svg") is original
    manager.registry.clear()
    assert manager.get_rit("media/nested/a.svg") is None
    manager.registry.add(replacement)
    assert manager.get_rit("media/nested/b.svg") is replacement


def test_late_registration_and_replacement_index_handlers_after_warmed_misses(
    tmp_path: Path,
) -> None:
    manager = ResourceManager(tmp_path)
    assert manager.get_rit("nested/a.svg") is None
    _write_svg(tmp_path / "nested/a.svg")
    record = manager.register_file(Path("nested/a.svg"))
    assert manager.get_rit("nested/a.svg") is record
    assert manager.get_rit("nested/b.svg") is None
    _write_blue_svg(tmp_path / "nested/b.svg")

    def replace(record: MediaRIT, *, ctx=None) -> MediaRIT:
        return record.model_copy(update={"label": f"handled_{record.path.stem}"})

    manager.register_index_handler(replace)
    manager.index_directory("nested")
    current = manager.get_rit("handled_b")
    assert current is not None and manager.get_rit("nested/b.svg") is current
    assert manager.get_rit("handled_a") is None
    assert manager.get_rit("nested/a.svg") is record
    current.path = tmp_path / "nested/changed.svg"
    assert manager.get_rit("nested/b.svg") is None
    assert manager.get_rit("nested/changed.svg") is current


def test_windows_path_equality_must_not_reuse_differently_spelled_relative_strings() -> None:
    # PureWindowsPath exercises Windows lexical rules without a Windows filesystem.
    root = PureWindowsPath("C:/media")
    upper = PureWindowsPath("C:/media/nested/Picture.svg")
    lower = PureWindowsPath("C:/media/nested/picture.svg")
    assert upper == lower and str(upper) != str(lower)
    manager = ResourceManager(root)
    record = _path_record(label="record").model_copy(update={"path": upper})
    manager.registry.add(record)
    assert manager.get_rit(str(upper.relative_to(root))) is record
    record.path = lower
    assert manager.get_rit(str(lower.relative_to(root))) is record
    assert manager.get_rit(str(upper.relative_to(root))) is None
