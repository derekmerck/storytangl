import pytest
from pathlib import Path

from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.story.fabula.world import World
from tangl.story.fabula.world_loader import WorldLoader


@pytest.fixture
def test_world_dirs(tmp_path: Path) -> list[Path]:
    """Create test world directories."""

    worlds_root = tmp_path / "worlds"
    worlds_root.mkdir()

    w1 = worlds_root / "world1"
    w1.mkdir()
    (w1 / "world.yaml").write_text("""
    uid: world1
    label: "World One"
    scripts: story.yaml
    """)
    (w1 / "story.yaml").write_text("""
    label: world1
    uid: 00000000-0000-0000-0000-000000000010
    metadata:
      title: "World One"
      author: "Tester"
    scenes: []
    """)
    (w1 / "media").mkdir()

    w2 = worlds_root / "world2"
    w2.mkdir()
    (w2 / "world.yaml").write_text("""
    uid: world2
    label: "World Two"
    scripts: story.yaml
    """)
    (w2 / "story.yaml").write_text("""
    label: world2
    uid: 00000000-0000-0000-0000-000000000020
    metadata:
      title: "World Two"
      author: "Tester"
    scenes: []
    """)
    (w2 / "media").mkdir()

    not_world = worlds_root / "not_a_world"
    not_world.mkdir()

    return [worlds_root]


def test_loader_discovers_bundles(test_world_dirs):
    """WorldLoader.discover_bundles() finds all valid bundles."""

    loader = WorldLoader(world_dirs=test_world_dirs)
    bundles = loader.discover_bundles()

    assert len(bundles) == 2
    assert "world1" in bundles
    assert "world2" in bundles
    assert "not_a_world" not in bundles


def test_loader_skips_missing_directories(tmp_path: Path):
    """Loader handles missing world_dirs gracefully."""

    missing_dir = tmp_path / "nonexistent"

    loader = WorldLoader(world_dirs=[missing_dir])
    bundles = loader.discover_bundles()

    assert len(bundles) == 0


def test_loader_handles_malformed_bundles(tmp_path: Path):
    """Loader logs errors for malformed bundles but continues."""

    worlds_root = tmp_path / "worlds"
    worlds_root.mkdir()

    good = worlds_root / "good"
    good.mkdir()
    (good / "world.yaml").write_text("""
    uid: good
    scripts: story.yaml
    """)
    (good / "story.yaml").write_text("uid: good\nlabel: good\nscenes: []")

    bad = worlds_root / "bad"
    bad.mkdir()
    (bad / "world.yaml").write_text("uid: bad\n  invalid: yaml: syntax:")

    loader = WorldLoader(world_dirs=[worlds_root])
    bundles = loader.discover_bundles()

    assert len(bundles) == 1
    assert "good" in bundles
    assert "bad" not in bundles


def test_loader_creates_world_with_resource_manager(media_mvp_root: Path):
    """WorldLoader.load_world() creates World with ResourceManager."""

    loader = WorldLoader(world_dirs=[media_mvp_root])
    loader.discover_bundles()

    world = loader.load_world("media_mvp")

    assert isinstance(world, World)
    assert world.name

    assert hasattr(world, "resource_manager")
    assert isinstance(world.resource_manager, ResourceManager)
    assert world.resource_manager.resource_path == world.bundle.media_dir

    assert hasattr(world, "bundle")
    assert world.bundle.manifest.uid == "media_mvp"


def test_loader_raises_on_unknown_world():
    """load_world() raises ValueError for unknown world_id."""

    loader = WorldLoader(world_dirs=[])
    loader.discover_bundles()

    with pytest.raises(ValueError, match="Unknown world"):
        loader.load_world("nonexistent")


def test_loader_single_file_script_only(tmp_path: Path):
    """Loader currently only supports single-file scripts."""

    bundle_dir = tmp_path / "multi"
    bundle_dir.mkdir()

    (bundle_dir / "world.yaml").write_text("""
    uid: multi
    scripts: [intro.yaml, main.yaml, epilogue.yaml]
    """)

    (bundle_dir / "intro.yaml").write_text("label: multi\nuid: 00000000-0000-0000-0000-000000000030\nscenes: []")
    (bundle_dir / "main.yaml").write_text("scenes: []")
    (bundle_dir / "epilogue.yaml").write_text("scenes: []")

    loader = WorldLoader(world_dirs=[tmp_path])
    loader.discover_bundles()

    with pytest.raises(NotImplementedError, match="Multi-file"):
        loader.load_world("multi")


def test_loader_reconciles_manifest_and_script_metadata(media_mvp_root: Path):
    """World construction merges manifest + script metadata."""

    loader = WorldLoader(world_dirs=[media_mvp_root])
    loader.discover_bundles()

    world = loader.load_world("media_mvp")

    assert world.name
    assert hasattr(world, "metadata")
