from __future__ import annotations

from pathlib import Path

import pytest

from tangl.media.media_resource.media_resource_registry import MediaResourceRegistry
from tangl.story.fabula.world_bundle import WorldBundle
from tangl.story.fabula.world_loader import WorldLoader


def test_bundle_loads_from_directory(media_mvp_path: Path) -> None:
    bundle = WorldBundle.load(media_mvp_path)

    assert bundle.manifest.uid == "media_mvp"
    assert bundle.media_dir.exists()
    assert len(bundle.script_paths) > 0


def test_loader_discovers_bundles(tmp_path: Path) -> None:
    (tmp_path / "world1").mkdir()
    (tmp_path / "world1" / "world.yaml").write_text(
        """
        uid: world1
        label: "World One"
        scripts: story.yaml
        """,
        encoding="utf-8",
    )

    (tmp_path / "world2").mkdir()
    (tmp_path / "world2" / "world.yaml").write_text(
        """
        uid: world2
        label: "World Two"
        scripts: story.yaml
        """,
        encoding="utf-8",
    )

    (tmp_path / "not_a_world").mkdir()

    loader = WorldLoader([tmp_path])
    bundles = loader.discover_bundles()

    assert len(bundles) == 2
    assert "world1" in bundles
    assert "world2" in bundles


def test_loader_creates_world_with_media_registry(media_mvp_path: Path) -> None:
    loader = WorldLoader([media_mvp_path.parent])
    loader.discover_bundles()

    world = loader.load_world("media_mvp")

    assert getattr(world, "uid", None) == "media_mvp"
    assert hasattr(world, "_bundle")
    assert isinstance(world.media_registry, MediaResourceRegistry)

    with pytest.raises(ValueError):
        loader.load_world("missing_world")
