from __future__ import annotations

from pathlib import Path

from tangl.loaders.compilers.media_compiler import MediaCompiler


def test_media_compiler_indexes_root_directory_when_no_hints(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    svg_path = media_dir / "cover.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="red"/></svg>',
        encoding="utf-8",
    )

    resource_manager = MediaCompiler().index(media_dir)

    assert resource_manager is not None
    rit = resource_manager.get_rit("cover.svg")
    assert rit is not None
    assert rit.path == svg_path


def test_media_compiler_indexes_organization_subdirs_only(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    portraits = media_dir / "portraits"
    ambience = media_dir / "ambience"
    portraits.mkdir(parents=True)
    ambience.mkdir(parents=True)

    hero = portraits / "hero.svg"
    hero.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<rect x="2" y="2" width="28" height="28" fill="blue"/></svg>',
        encoding="utf-8",
    )
    wind = ambience / "wind.svg"
    wind.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="12" fill="green"/></svg>',
        encoding="utf-8",
    )

    resource_manager = MediaCompiler().index(
        media_dir,
        organization_hints={"portraits": {"role": "avatar"}},
    )

    assert resource_manager is not None
    assert resource_manager.get_rit("hero.svg") is not None
    assert resource_manager.get_rit("wind.svg") is None


def test_media_compiler_returns_none_for_missing_directory(tmp_path: Path) -> None:
    missing_dir = tmp_path / "does_not_exist"

    resource_manager = MediaCompiler().index(missing_dir)

    assert resource_manager is None


def test_media_compiler_applies_index_handlers(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    svg_path = media_dir / "scene-road-book2.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<rect x="2" y="2" width="28" height="28" fill="blue"/></svg>',
        encoding="utf-8",
    )

    def _parse_stem(record, *, ctx=None):
        stem = record.path.stem
        label, *tags = stem.split("-")
        record.label = label
        record.tags |= set(tags)
        return record

    resource_manager = MediaCompiler().index(
        media_dir,
        index_handlers=[_parse_stem],
    )

    assert resource_manager is not None
    rit = resource_manager.get_rit("scene")
    assert rit is not None
    assert rit.path == svg_path
    assert {"road", "book2", "scope:world"}.issubset(set(rit.tags or set()))
