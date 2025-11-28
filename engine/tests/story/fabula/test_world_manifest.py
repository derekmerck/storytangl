from __future__ import annotations

import pytest
import yaml

from tangl.story.fabula.world_manifest import WorldManifest


def test_manifest_parses_yaml() -> None:
    yaml_text = """
    uid: test_world
    label: "Test World"
    scripts: story.yaml
    media_dir: media
    """
    manifest = WorldManifest.model_validate(yaml.safe_load(yaml_text))
    assert manifest.uid == "test_world"
    assert manifest.scripts == ["story.yaml"]


def test_manifest_normalizes_scripts() -> None:
    manifest = WorldManifest(uid="test", label="Test", scripts="main.yaml")
    assert manifest.scripts == ["main.yaml"]


def test_manifest_validates_uid() -> None:
    with pytest.raises(ValueError):
        WorldManifest(uid="../evil", label="Bad", scripts=["x.yaml"])
