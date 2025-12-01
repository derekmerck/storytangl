from __future__ import annotations

from pathlib import Path

from tangl.compilers.world_config import (
    FileSource,
    TreeSource,
    WorldConfig,
)


def test_world_config_parses_sample_bundle() -> None:
    config_path = Path("engine/tests/resources/worlds/world_config/world.yaml")

    world_config = WorldConfig.model_validate_yaml(config_path)

    assert world_config.id == "sample_world"
    assert world_config.domain.module == "tangl.demo.domain"
    assert world_config.media is not None
    assert world_config.media.roots == ["media"]

    assert world_config.scripts
    file_script = world_config.scripts[0]
    assert isinstance(file_script.source, FileSource)
    assert file_script.source.entry_label == "start"

    tree_script = world_config.scripts[1]
    assert isinstance(tree_script.source, TreeSource)
    assert tree_script.source.entry == {"block_label": "intro"}
    assert "blocks" in tree_script.source.conventions
    assert tree_script.source.conventions["blocks"].glob == "*.yaml"
