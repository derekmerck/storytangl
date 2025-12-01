from __future__ import annotations

from tangl.compilers.world_loader import load_scripts, load_world_config
from tangl.story.fabula.world_loader import build_world_from_bundle


def test_load_world_from_bundle(add_worlds_to_sys_path) -> None:
    cfg, root = load_world_config("media_mvp")
    assert cfg.id == "media_mvp"
    assert root.name == "media_mvp"

    scripts = load_scripts(cfg, root)
    script = scripts[cfg.scripts[0].id]
    assert script.metadata.entry_label == "start"
    assert "start" in script.blocks

    world, graphs = build_world_from_bundle("media_mvp")
    assert getattr(world, "uid", None) == "media_mvp"
    assert graphs[cfg.scripts[0].id].initial_cursor_id is not None
    rit = world.resource_manager.get_rit("test_image.svg")
    assert rit is not None
    assert world.media_registry is world.resource_manager.registry


def test_build_world_from_demo_bundle(add_worlds_to_sys_path) -> None:
    cfg, root = load_world_config("demo_world")

    assert cfg.id == "demo_world"
    assert root.name == "demo_world"

    scripts = load_scripts(cfg, root)
    assert set(scripts) == {"demo_story"}

    world, graphs = build_world_from_bundle("demo_world")

    assert world.uid == cfg.id
    assert world.script_manager.master_script.metadata.start_at == "start"

    start_node = graphs["demo_story"].get(graphs["demo_story"].initial_cursor_id)
    assert start_node is not None
    assert start_node.label == "start"
