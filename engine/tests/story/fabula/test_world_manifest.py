import pytest
from yaml import safe_load

from tangl.ir.core_ir.script_metadata_model import ScriptMetadata
from tangl.story.fabula.world_manifest import WorldManifest


def test_manifest_parses_yaml_with_embedded_metadata():
    """WorldManifest embeds ScriptMetadata."""

    yaml_text = """
    uid: test_world
    label: "Test World"
    scripts: story.yaml
    media_dir: media
    metadata:
      title: "Test World Title"
      author: "Tester"
      summary: "A test world"
    """

    manifest = WorldManifest.model_validate(safe_load(yaml_text))

    assert manifest.uid == "test_world"
    assert manifest.scripts == ["story.yaml"]
    assert manifest.metadata is not None
    assert manifest.metadata.title == "Test World Title"
    assert manifest.metadata.author == "Tester"


def test_manifest_effective_label_priority():
    """effective_label follows priority: label > metadata.title > uid."""

    m1 = WorldManifest(
        uid="test",
        label="Explicit Label",
        scripts=["x.yaml"],
        metadata=ScriptMetadata(title="Metadata Title", author="X"),
    )
    assert m1.effective_label == "Explicit Label"

    m2 = WorldManifest(
        uid="test",
        scripts=["x.yaml"],
        metadata=ScriptMetadata(title="Metadata Title", author="X"),
    )
    assert m2.effective_label == "Metadata Title"

    m3 = WorldManifest(
        uid="test_world",
        scripts=["x.yaml"],
    )
    assert m3.effective_label == "test_world"


def test_manifest_normalizes_scripts_scalar_to_list():
    """Single script string normalized to list."""

    manifest = WorldManifest(
        uid="test",
        label="Test",
        scripts="main.yaml",
    )

    assert manifest.scripts == ["main.yaml"]
    assert manifest.script_paths_relative == ["main.yaml"]


def test_manifest_preserves_script_list():
    """Script list preserved as-is."""

    manifest = WorldManifest(
        uid="test",
        label="Test",
        scripts=["intro.yaml", "scenes.yaml", "actors.yaml"],
    )

    assert manifest.scripts == ["intro.yaml", "scenes.yaml", "actors.yaml"]


def test_manifest_validates_uid_filesystem_safe():
    """uid must be filesystem-safe."""

    WorldManifest(uid="valid_world", label="X", scripts=["x.yaml"])
    WorldManifest(uid="valid-world", label="X", scripts=["x.yaml"])
    WorldManifest(uid="world123", label="X", scripts=["x.yaml"])

    with pytest.raises(ValueError, match="filesystem-safe"):
        WorldManifest(uid="../evil", label="X", scripts=["x.yaml"])

    with pytest.raises(ValueError, match="filesystem-safe"):
        WorldManifest(uid="bad/path", label="X", scripts=["x.yaml"])

    with pytest.raises(ValueError, match="filesystem-safe"):
        WorldManifest(uid="bad path", label="X", scripts=["x.yaml"])


def test_manifest_defaults():
    """Default values applied correctly."""

    manifest = WorldManifest(
        uid="minimal",
        scripts="story.yaml",
    )

    assert manifest.version == "1.0"
    assert manifest.media_dir == "media"
    assert manifest.tags == []
    assert manifest.metadata is None
    assert manifest.python_packages is None
    assert manifest.plugins is None


def test_manifest_script_paths_relative():
    """script_paths_relative returns list of relative paths."""

    manifest = WorldManifest(
        uid="test",
        scripts=["scenes/intro.yaml", "scenes/chapter1.yaml"],
    )

    assert manifest.script_paths_relative == [
        "scenes/intro.yaml",
        "scenes/chapter1.yaml",
    ]
