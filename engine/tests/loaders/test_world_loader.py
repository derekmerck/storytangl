from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tangl.loaders.bundle import WorldBundle
from tangl.loaders.compiler import ScriptCompiler, WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import World


class _BridgeScriptCompiler(ScriptCompiler):
    """Test helper exposing a custom per-file loader."""

    def load_from_path(self, script_path: Path) -> dict:
        text = script_path.read_text(encoding="utf-8").strip()
        return {
            "label": "bridge_world",
            "metadata": {"title": text or "bridge", "author": "tests"},
            "scenes": {},
        }


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


def test_loader_creates_runtime_world_with_media_registry(media_mvp_path: Path) -> None:
    registry = WorldRegistry([media_mvp_path.parent])

    world = registry.get_world("media_mvp")

    assert world.label == "media_mvp"
    assert world.bundle is not None
    assert world.resources is not None
    assert world.resources.registry

    rit = world.resources.get_rit("test_image.svg")
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
          author: TanglDev
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

    assert world.metadata.get("author") == "TanglDev"


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


def test_story_map_manifest_drives_script_resolution_and_codec(tmp_path: Path) -> None:
    bundle_root = tmp_path / "stories_world"
    scripts_dir = bundle_root / "content"
    scripts_dir.mkdir(parents=True)

    (bundle_root / "world.yaml").write_text(
        """
        label: stories_world
        codec: near_native
        stories:
          book1:
            scripts:
              - content/book1.yaml
          book2:
            codec: yaml
            scripts:
              - content/book2.yaml
        """,
        encoding="utf-8",
    )

    (scripts_dir / "book1.yaml").write_text("label: book1\nscenes: {}\n", encoding="utf-8")
    (scripts_dir / "book2.yaml").write_text("label: book2\nscenes: {}\n", encoding="utf-8")

    bundle = WorldBundle.load(bundle_root)

    assert bundle.manifest.is_anthology
    assert bundle.manifest.story_keys() == ["book1", "book2"]
    assert bundle.get_script_paths("book1") == [scripts_dir / "book1.yaml"]
    assert bundle.get_story_codec("book1") == "near_native"
    assert bundle.get_story_codec("book2") == "yaml"


def test_custom_script_loader_bridge_used_when_codec_not_explicit(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bridge_world"
    bundle_root.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: bridge_world
        scripts: story.custom
        """,
        encoding="utf-8",
    )
    (bundle_root / "story.custom").write_text("Bridge Story", encoding="utf-8")

    bundle = WorldBundle.load(bundle_root)
    world = WorldCompiler(script_compiler=_BridgeScriptCompiler()).compile(
        bundle,
    )

    assert world.label == "bridge_world"
    assert world.metadata.get("title") == "Bridge Story"


def test_explicit_codec_disables_custom_script_loader_bridge(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bridge_world_explicit"
    bundle_root.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: bridge_world_explicit
        codec: near_native
        scripts: story.custom
        """,
        encoding="utf-8",
    )
    (bundle_root / "story.custom").write_text("not: [valid", encoding="utf-8")

    bundle = WorldBundle.load(bundle_root)

    with pytest.raises(Exception):
        WorldCompiler(script_compiler=_BridgeScriptCompiler()).compile(
            bundle,
        )


def test_codec_merge_collisions_are_reported(tmp_path: Path) -> None:
    bundle_root = tmp_path / "merge_world"
    bundle_root.mkdir()
    scripts_dir = bundle_root / "scripts"
    scripts_dir.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: merge_world
        scripts:
          - scripts/a.yaml
          - scripts/b.yaml
        metadata:
          author: Tests
        """,
        encoding="utf-8",
    )

    (scripts_dir / "a.yaml").write_text(
        """
        label: merge_world
        metadata:
          title: A
        scenes: {}
        """,
        encoding="utf-8",
    )
    (scripts_dir / "b.yaml").write_text(
        """
        label: merge_world
        metadata:
          title: B
        scenes: {}
        """,
        encoding="utf-8",
    )

    bundle = WorldBundle.load(bundle_root)
    warnings = WorldCompiler()._decode_story_data(bundle=bundle, story_key=None).warnings

    assert warnings
    assert any("overwrote top-level keys" in warning for warning in warnings)


def test_world_compile_preserves_compile_issues_separately_from_codec_warnings(tmp_path: Path) -> None:
    bundle_root = tmp_path / "diagnostic_world"
    bundle_root.mkdir()
    scripts_dir = bundle_root / "scripts"
    scripts_dir.mkdir()

    (bundle_root / "world.yaml").write_text(
        """
        label: diagnostic_world
        scripts:
          - scripts/a.yaml
          - scripts/b.yaml
        """,
        encoding="utf-8",
    )

    (scripts_dir / "a.yaml").write_text(
        """
        label: diagnostic_world
        metadata:
          start_at: intro.start
        scenes:
          intro:
            blocks:
              start:
                content: Start
                roles:
                  - label: host
                    actor_ref: missing_actor
        """,
        encoding="utf-8",
    )
    (scripts_dir / "b.yaml").write_text(
        """
        metadata:
          title: Override
        """,
        encoding="utf-8",
    )

    bundle = WorldBundle.load(bundle_root)
    world = WorldCompiler().compile(bundle)

    assert [issue.code for issue in world.bundle.issues] == ["compile:dangling_actor_ref"]
    assert any("overwrote top-level keys" in warning for warning in world.metadata["codec_warnings"])
    assert "loss_records" not in world.bundle.codec_state


@pytest.mark.skip(
    reason=(
        "Retired from the cutover parity gate: validates runtime37 world internals "
        "(domain_manager/resource_manager wiring). Runtime equivalent coverage is "
        "provided by test_compile_anthology_shares_world_facets."
    )
)
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

    (bundle_root / "domain").mkdir()

    domain_pkg = bundle_root / "anthology"
    domain_pkg.mkdir(parents=True)
    (domain_pkg / "__init__.py").write_text("", encoding="utf-8")
    (domain_pkg / "domain.py").write_text(
        """
from tangl.core import Entity


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
    assert not hasattr(world_one, "script_manager")
    assert not hasattr(world_two, "script_manager")
    assert world_one.templates is not world_two.templates

    assert "DomainCharacter" in world_one.domain_manager.class_registry
    assert world_one.metadata["author"] == "Steve"
    assert world_one.metadata["title"] == "Book One"
    assert world_two.metadata["author"] == "Steve"
    assert world_two.metadata["title"] == "book2"


def test_compile_anthology_shares_world_facets(tmp_path: Path) -> None:
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

    (bundle_root / "domain").mkdir()
    domain_pkg = bundle_root / "anthology"
    domain_pkg.mkdir(parents=True)
    (domain_pkg / "__init__.py").write_text("", encoding="utf-8")
    (domain_pkg / "domain.py").write_text(
        """
from tangl.core import Entity


class DomainCharacter(Entity):
    ...
        """,
        encoding="utf-8",
    )

    bundle = WorldBundle.load(bundle_root)
    compiler = WorldCompiler()
    anthology = compiler.compile_anthology(bundle)

    world_one = anthology["book1"]
    world_two = anthology["book2"]

    assert isinstance(world_one, World)
    assert isinstance(world_two, World)
    assert world_one.domain is world_two.domain
    assert world_one.assets is world_two.assets
    assert world_one.resources is world_two.resources
    assert not hasattr(world_one, "script_manager")
    assert not hasattr(world_two, "script_manager")
    assert world_one.templates is world_one.bundle.template_registry
    assert world_two.templates is world_two.bundle.template_registry
    assert world_one.templates is not world_two.templates
    assert "DomainCharacter" in world_one.domain.class_registry
    assert world_one.domain.dispatch_registry in world_one.get_authorities()


def test_compiler_adds_bundle_root_for_domain_imports(tmp_path: Path) -> None:
    bundle_root = tmp_path / "domain_world"
    bundle_root.mkdir()
    (bundle_root / "domain").mkdir()

    package_dir = bundle_root / "domain_world"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "domain.py").write_text(
        """
from tangl.core import Entity


class DomainCharacter(Entity):
    ...
        """,
        encoding="utf-8",
    )

    (bundle_root / "world.yaml").write_text(
        """
label: domain_world
scripts: script.yaml
        """,
        encoding="utf-8",
    )

    (bundle_root / "script.yaml").write_text(
        """
label: domain_world
metadata:
  title: Domain World
  author: Tests
scenes: {}
        """,
        encoding="utf-8",
    )

    bundle = WorldBundle.load(bundle_root)
    compiler = WorldCompiler()

    original_sys_path = list(sys.path)
    try:
        world = compiler.compile(bundle)

        assert isinstance(world, World)
        assert world.domain is not None
        assert "DomainCharacter" in world.domain.class_registry
        assert world.domain.dispatch_registry in world.get_authorities()
        assert str(bundle_root) in sys.path
        assert str(bundle.domain_dir) not in sys.path
    finally:
        sys.path[:] = original_sys_path
