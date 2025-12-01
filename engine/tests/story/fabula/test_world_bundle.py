from __future__ import annotations

from tangl.story.fabula.world_bundle import WorldBundle


def test_world_bundle_loads_via_compiler(add_worlds_to_sys_path) -> None:
    bundle = WorldBundle.load("demo_world")

    assert bundle.config.id == "demo_world"
    assert bundle.bundle_root.name == "demo_world"
    assert bundle.media_dir is None
    assert bundle.script_paths == [bundle.bundle_root / "content" / "demo.yaml"]
