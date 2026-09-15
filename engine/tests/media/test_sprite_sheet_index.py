"""Indexing finds sprite sheets and attaches each to the still it belongs to.

The still stays exactly what it was; its sheets ride on it. The claims under test
are that linking does not depend on which file is indexed first, that a sidecar
export cannot contradict its filename, and that the attachment survives a story
copying the still into its graph -- the reason it is attached rather than looked up.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from tangl.core import Graph
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media.media_resource.sprite_sheet_index import SpriteSheetError


def _png(path: Path, size: tuple[int, int], shade: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, (shade, shade, shade, 255)).save(path)
    return path


def _export(image: str, size: tuple[int, int], cells: int, tags: list[dict], durations: list[int]) -> dict:
    cw = size[0] // cells
    return {
        "frames": [
            {"filename": f"{image} {i}", "frame": {"x": i * cw, "y": 0, "w": cw, "h": size[1]}, "duration": d}
            for i, d in enumerate(durations)
        ],
        "meta": {"image": image, "size": {"w": size[0], "h": size[1]}, "frameTags": tags},
    }


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    _png(tmp_path / "images" / "hero.png", (10, 12), 10)
    return tmp_path


def _still(manager: ResourceManager, name: str = "hero.png") -> MediaRIT:
    return manager.get_rit(name)


def test_a_named_sheet_attaches_to_its_still_with_the_manifest_its_name_implies(pack: Path) -> None:
    _png(pack / "images" / "hero-idle-4x1-800ms.png", (40, 12), 20)
    manager = ResourceManager(pack)
    manager.index_directory("images")

    [ref] = _still(manager).sprite_sheets

    assert ref.path.name == "hero-idle-4x1-800ms.png"
    assert ref.manifest.clip_names() == ["idle"]
    assert [f.duration for f in ref.manifest.frames] == [200, 200, 200, 200]


def test_the_still_is_otherwise_untouched(pack: Path) -> None:
    """A client that knows nothing of sheets gets exactly what it got before."""

    before = ResourceManager(pack)
    before.index_directory("images")
    _png(pack / "images" / "hero-idle-2x1.png", (20, 12), 20)
    after = ResourceManager(pack)
    after.index_directory("images")

    assert _still(after).path == _still(before).path
    assert _still(after).content_hash() == _still(before).content_hash()
    assert _still(after).sprite_sheet is None


def test_linking_does_not_depend_on_which_file_is_indexed_first(pack: Path) -> None:
    """A sheet always sorts before its still ("-" < "."), so a per-file step never sees both."""

    sheet = _png(pack / "images" / "hero-idle-2x1.png", (20, 12), 20)
    manager = ResourceManager(pack)
    manager.register_file(sheet)
    manager.register_file(pack / "images" / "hero.png")

    assert [r.path.name for r in _still(manager).sprite_sheets] == ["hero-idle-2x1.png"]


def test_reindexing_does_not_attach_a_sheet_twice(pack: Path) -> None:
    _png(pack / "images" / "hero-idle-2x1.png", (20, 12), 20)
    manager = ResourceManager(pack)
    manager.index_directory("images")
    manager.index_directory("images")

    assert len(_still(manager).sprite_sheets) == 1


def test_a_sidecar_export_is_authoritative(pack: Path) -> None:
    _png(pack / "images" / "hero-2x1.png", (20, 12), 20)
    (pack / "images" / "hero-2x1.json").write_text(json.dumps(
        _export("hero-2x1.png", (20, 12), 2, [{"name": "idle", "from": 0, "to": 1}], [1800, 200])
    ))
    manager = ResourceManager(pack)
    manager.index_directory("images")

    [ref] = _still(manager).sprite_sheets
    assert [f.duration for f in ref.manifest.frames] == [1800, 200]


@pytest.mark.parametrize(
    ("image_name", "size", "export", "message"),
    [
        ("hero-2x1.png", (20, 12), _export("hero-2x1.png", (30, 12), 2, [], [100, 100]), "image is 20x12"),
        ("hero-2x1.png", (20, 12), _export("other.png", (20, 12), 2, [], [100, 100]), "names image 'other.png'"),
        ("hero-4x1.png", (40, 12), _export("hero-4x1.png", (40, 12), 2, [], [100, 100]), "its name says 4x1"),
        ("hero-call-2x1.png", (20, 12), _export("hero-call-2x1.png", (20, 12), 2, [{"name": "idle", "from": 0, "to": 1}], [100, 100]), "names clip 'call'"),
        ("hero-idle-2x1-500ms.png", (20, 12), _export("hero-idle-2x1-500ms.png", (20, 12), 2, [{"name": "idle", "from": 0, "to": 1}], [100, 100]), "says 500 ms"),
    ],
)
def test_a_sidecar_that_contradicts_its_filename_fails_at_load(pack, image_name, size, export, message) -> None:
    _png(pack / "images" / image_name, size, 20)
    (pack / "images" / image_name).with_suffix(".json").write_text(json.dumps(export))

    with pytest.raises(SpriteSheetError, match=message):
        ResourceManager(pack).index_directory("images")


def test_several_sheets_may_serve_one_still_if_their_clips_differ(pack: Path) -> None:
    _png(pack / "images" / "hero-idle-2x1.png", (20, 12), 20)
    _png(pack / "images" / "hero-call-1x1.png", (10, 12), 30)
    manager = ResourceManager(pack)
    manager.index_directory("images")

    assert [r.manifest.clip_names() for r in _still(manager).sprite_sheets] == [["call"], ["idle"]]


def test_two_sheets_defining_one_clip_for_one_still_are_refused(pack: Path) -> None:
    _png(pack / "images" / "hero-idle-2x1.png", (20, 12), 20)
    _png(pack / "images" / "hero-idle-4x1.png", (40, 12), 30)

    with pytest.raises(SpriteSheetError, match="both define clip"):
        ResourceManager(pack).index_directory("images")


def test_a_sheet_with_no_still_is_inert_rather_than_an_error(tmp_path: Path) -> None:
    _png(tmp_path / "images" / "ghost-idle-2x1.png", (20, 12), 20)
    manager = ResourceManager(tmp_path)
    manager.index_directory("images")

    assert manager.get_rit("ghost-idle-2x1.png").sprite_sheet.clip_names() == ["idle"]


def test_loose_frame_names_are_stills_not_sheets(pack: Path) -> None:
    """#418's ``-01`` suffix stays a separate convention."""

    _png(pack / "images" / "hero-idle-01.png", (10, 12), 20)
    manager = ResourceManager(pack)
    manager.index_directory("images")

    assert manager.get_rit("hero-idle-01.png").sprite_sheet is None
    assert _still(manager).sprite_sheets == []


def test_sheets_survive_a_story_copying_the_still_into_its_graph(pack: Path) -> None:
    """The reason sheets are attached, not looked up.

    A story binds a copy of the still to its own graph, where the world's inventory
    is unreachable. Asserted through a full graph round trip, so a regression that
    moved discovery back to an inventory search would fail here rather than in a
    reloaded session.
    """

    _png(pack / "images" / "hero-idle-2x1.png", (20, 12), 20)
    manager = ResourceManager(pack)
    manager.index_directory("images")

    graph = Graph()
    graph.add(MediaRIT.structure(_still(manager).unstructure()))
    restored = next(e for e in Graph.structure(graph.unstructure()).values() if isinstance(e, MediaRIT))

    assert [r.path.name for r in restored.sprite_sheets] == ["hero-idle-2x1.png"]
    assert restored.sprite_sheets[0].manifest.clip_names() == ["idle"]
