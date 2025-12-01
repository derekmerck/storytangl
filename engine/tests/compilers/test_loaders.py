from __future__ import annotations

import yaml

from tangl.compilers.loaders import get_loader
from tangl.compilers.loaders import simple_single_file, simple_tree
from tangl.compilers.world_config import (
    DomainConfig,
    FileSource,
    ScriptConfig,
    TreeConventions,
    TreeSource,
    WorldConfig,
)


def make_world_config() -> WorldConfig:
    return WorldConfig(
        id="world",
        title="World",
        kind="demo",
        domain=DomainConfig(module="demo.domain"),
    )


def test_simple_single_file_loader_round_trip(tmp_path) -> None:
    script_path = tmp_path / "demo.yaml"
    script_path.write_text(
        yaml.safe_dump(
            {
                "entry": "begin",
                "blocks": {"begin": {"text": "Hello"}},
                "actors": {"hero": {"name": "Hero"}},
                "custom": {"note": "extra"},
            }
        ),
        encoding="utf-8",
    )

    script_cfg = ScriptConfig(
        id="demo",
        label="Demo",
        loader="builtin:simple_single_file",
        source=FileSource(type="file", path="demo.yaml"),
    )

    loader = simple_single_file.SimpleSingleFileLoader()
    script = loader.load(tmp_path, make_world_config(), script_cfg)

    assert script.metadata.id == "demo"
    assert script.metadata.entry_label == "begin"
    assert script.blocks["begin"]["text"] == "Hello"
    assert script.actors["hero"]["name"] == "Hero"
    assert script.extra["custom"] == {"note": "extra"}

    registry_loader = get_loader("builtin:simple_single_file")
    registry_script = registry_loader.load(tmp_path, make_world_config(), script_cfg)
    assert registry_script.blocks == script.blocks


def test_simple_tree_loader_collects_tree(tmp_path) -> None:
    root = tmp_path / "scripts"
    (root / "blocks").mkdir(parents=True)
    (root / "actors").mkdir()
    (root / "chapters" / "prologue" / "scenes").mkdir(parents=True)

    (root / "blocks" / "start.yaml").write_text(
        yaml.safe_dump({"text": "Start"}),
        encoding="utf-8",
    )
    (root / "actors" / "hero.yaml").write_text(
        yaml.safe_dump({"name": "Hero"}),
        encoding="utf-8",
    )
    (root / "chapters" / "prologue" / "scenes" / "intro.yaml").write_text(
        yaml.safe_dump({"text": "Scene intro"}),
        encoding="utf-8",
    )

    script_cfg = ScriptConfig(
        id="tree",
        label="Tree",
        loader="builtin:simple_tree",
        source=TreeSource(
            type="tree",
            root="scripts",
            entry={"block_label": "start"},
            conventions={
                "blocks": TreeConventions(obj_cls="tangl.story.Block"),
                "actors": TreeConventions(obj_cls="tangl.story.Actor"),
            },
            nested={"scenes": TreeConventions(obj_cls="tangl.story.Scene")},
        ),
    )

    loader = simple_tree.SimpleTreeLoader()
    script = loader.load(tmp_path, make_world_config(), script_cfg)

    assert script.metadata.entry_label == "start"
    assert script.blocks["start"] == {"text": "Start"}
    assert script.actors["hero"] == {"name": "Hero"}
    assert script.extra["scenes"]["intro"] == {"text": "Scene intro"}

    registry_loader = get_loader("builtin:simple_tree")
    registry_script = registry_loader.load(tmp_path, make_world_config(), script_cfg)
    assert registry_script.blocks == script.blocks
