from pathlib import Path

import pytest

from tangl.story.fabula.world_bundle import WorldBundle


def test_bundle_loads_from_directory(media_mvp_path: Path):
    """WorldBundle.load() reads world.yaml and validates structure."""

    bundle = WorldBundle.load(media_mvp_path)

    assert bundle.manifest.uid == "media_mvp"
    assert bundle.bundle_root == media_mvp_path
    assert bundle.media_dir == media_mvp_path / "media"
    assert bundle.media_dir.exists()
    assert len(bundle.script_paths) == 1
    assert bundle.script_paths[0].exists()


def test_bundle_validates_uid_matches_directory(tmp_path: Path):
    """Bundle refuses to load if uid doesn't match directory name."""

    wrong_name_path = tmp_path / "wrong_name"
    wrong_name_path.mkdir()
    (wrong_name_path / "world.yaml").write_text("""
    uid: different
    scripts: story.yaml
    media_dir: media
    """)

    with pytest.raises(ValueError, match="must match directory name"):
        WorldBundle.load(wrong_name_path)


def test_bundle_resolves_absolute_paths(tmp_path: Path):
    """Bundle properties return absolute paths."""

    bundle_dir = tmp_path / "test_world"
    bundle_dir.mkdir()

    (bundle_dir / "world.yaml").write_text("""
    uid: test_world
    scripts: [scenes/intro.yaml, scenes/main.yaml]
    media_dir: assets/media
    """)

    bundle = WorldBundle.load(bundle_dir)

    assert bundle.bundle_root.is_absolute()
    assert all(path.is_absolute() for path in bundle.script_paths)
    assert bundle.media_dir.is_absolute()

    assert bundle.script_paths[0] == bundle_dir.resolve() / "scenes/intro.yaml"
    assert bundle.script_paths[1] == bundle_dir.resolve() / "scenes/main.yaml"
    assert bundle.media_dir == bundle_dir.resolve() / "assets/media"


def test_bundle_missing_manifest_raises_error(tmp_path: Path):
    """Loading directory without world.yaml raises FileNotFoundError."""

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="No world.yaml"):
        WorldBundle.load(empty_dir)
