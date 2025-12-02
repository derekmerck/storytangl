from __future__ import annotations

from pathlib import Path

import pytest

from tangl.loaders.bundle import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry


def test_bundle_loads_from_directory(media_mvp_path: Path) -> None:
    bundle = WorldBundle.load(media_mvp_path)

    assert bundle.manifest.label == "media_mvp"
    assert bundle.media_dir.exists()
    assert len(bundle.script_paths) > 0


def test_loader_discovers_bundles(tmp_path: Path) -> None:
    (tmp_path / "world1").mkdir()
    (tmp_path / "world1" / "world.yaml").write_text(
        """
        label: world1
        scripts: story.yaml
        """,
        encoding="utf-8",
    )

    (tmp_path / "world2").mkdir()
    (tmp_path / "world2" / "world.yaml").write_text(
        """
        label: world2
        scripts: story.yaml
        """,
        encoding="utf-8",
    )

    (tmp_path / "not_a_world").mkdir()

    registry = WorldRegistry([tmp_path])
    bundles = registry.bundles

    assert len(bundles) == 2
    assert "world1" in bundles
    assert "world2" in bundles


def test_loader_creates_world_with_media_registry(media_mvp_path: Path) -> None:
    registry = WorldRegistry([media_mvp_path.parent])

    world = registry.get_world("media_mvp")

    assert world.label == "media_mvp"
    assert hasattr(world, "_bundle")
    assert world.resource_manager.registry

    rit = world.resource_manager.get_rit("test_image.svg")
    assert rit is not None

    with pytest.raises(ValueError):
        registry.get_world("missing_world")


def test_manifest_metadata_inheritance(tmp_path: Path) -> None:
    bundle_root = tmp_path / "my_world"
    bundle_root.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: my_world
        metadata:
          author: Derek
        """,
        encoding="utf-8",
    )

    (bundle_root / "script.yaml").write_text(
        """
        label: my_world
        scenes: {}
        """,
        encoding="utf-8",
    )

    registry = WorldRegistry([tmp_path], compiler=WorldCompiler())

    world = registry.get_world("my_world")

    assert world.metadata.get("author") == "Derek"


def test_bundle_label_must_match_directory_name(tmp_path: Path) -> None:
    bundle_root = tmp_path / "folder_name"
    bundle_root.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: different_label
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        WorldBundle.load(bundle_root)


def test_script_discovery_falls_back_to_script_yaml(tmp_path: Path) -> None:
    bundle_root = tmp_path / "fallback_world"
    bundle_root.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: fallback_world
        """,
        encoding="utf-8",
    )

    script_path = bundle_root / "script.yaml"
    script_path.write_text(
        """
        label: fallback_world
        scenes: {}
        """,
        encoding="utf-8",
    )

    bundle = WorldBundle.load(bundle_root)

    assert bundle.get_script_paths() == [script_path]


def test_script_discovery_uses_scripts_directory(tmp_path: Path) -> None:
    bundle_root = tmp_path / "nested_world"
    scripts_dir = bundle_root / "scripts"
    scripts_dir.mkdir(parents=True)

    (bundle_root / "world.yaml").write_text(
        """
        label: nested_world
        """,
        encoding="utf-8",
    )

    script_a = scripts_dir / "a.yaml"
    script_b = scripts_dir / "nested" / "b.yaml"
    script_b.parent.mkdir()
    script_a.write_text("label: nested_world\nscenes: {}\n", encoding="utf-8")
    script_b.write_text("label: nested_world\nmetadata:\n  title: B\n", encoding="utf-8")

    bundle = WorldBundle.load(bundle_root)

    paths = bundle.get_script_paths()

    assert paths == [script_a, script_b]


def test_compile_anthology_shares_domain_and_media(tmp_path: Path) -> None:
    bundle_root = tmp_path / "anthology"
    scripts_dir = bundle_root / "scripts"
    media_dir = bundle_root / "media"
    scripts_dir.mkdir(parents=True)
    media_dir.mkdir()
    (media_dir / "cover.svg").write_text(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\"></svg>",
        encoding="utf-8",
    )

    (bundle_root / "world.yaml").write_text(
        """
        label: anthology
        scripts:
          book1: scripts/book1.yaml
          book2: scripts/book2.yaml
        metadata:
          author: Steve
        """,
        encoding="utf-8",
    )

    (scripts_dir / "book1.yaml").write_text(
        """
        label: book1
        metadata:
          title: Book One
        scenes: {}
        """,
        encoding="utf-8",
    )
    (scripts_dir / "book2.yaml").write_text(
        """
        label: book2
        scenes: {}
        """,
        encoding="utf-8",
    )

    domain_pkg = bundle_root / "domain" / "anthology"
    domain_pkg.mkdir(parents=True)
    (domain_pkg / "__init__.py").write_text("", encoding="utf-8")
    (domain_pkg / "domain.py").write_text(
        """
from tangl.core.entity import Entity


class DomainCharacter(Entity):
    ...
        """,
        encoding="utf-8",
    )

    bundle = WorldBundle.load(bundle_root)
    compiler = WorldCompiler()

    anthology = compiler.compile_anthology(bundle)

    assert set(anthology.keys()) == {"book1", "book2"}

    world_one = anthology["book1"]
    world_two = anthology["book2"]

    assert world_one.domain_manager is world_two.domain_manager
    assert world_one.resource_manager is world_two.resource_manager
    assert world_one.asset_manager is not world_two.asset_manager
    assert world_one.script_manager is not world_two.script_manager

    assert "DomainCharacter" in world_one.domain_manager.class_registry
    assert world_one.metadata["author"] == "Steve"
    assert world_one.metadata["title"] == "Book One"
    assert world_two.metadata["author"] == "Steve"
    assert world_two.metadata["title"] == "book2"
