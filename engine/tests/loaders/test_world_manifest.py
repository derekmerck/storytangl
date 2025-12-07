from __future__ import annotations

import pytest
import yaml

from tangl.loaders.manifest import WorldManifest


def test_manifest_parses_yaml() -> None:
    yaml_text = """
    label: test_world
    scripts: story.yaml
    media_dir: media
    metadata:
      author: Derek
    """
    manifest = WorldManifest.model_validate(yaml.safe_load(yaml_text))
    assert manifest.scripts == ["story.yaml"]
    assert manifest.metadata["author"] == "Derek"


def test_manifest_normalizes_scripts() -> None:
    manifest = WorldManifest(label="test", scripts="main.yaml")
    assert manifest.scripts == ["main.yaml"]


def test_manifest_reports_anthology() -> None:
    manifest = WorldManifest(label="anthology", scripts={"book1": "one.yaml"})

    assert manifest.is_anthology
    assert manifest.story_keys() == ["book1"]
