from __future__ import annotations

from pathlib import Path

import pytest

from tangl.compilers.world_loader import load_scripts, load_world_config


@pytest.fixture
def add_worlds_to_sys_path(monkeypatch) -> Path:
    worlds_path = Path(__file__).resolve().parents[2] / "resources" / "worlds"
    monkeypatch.syspath_prepend(str(worlds_path))
    return worlds_path


def test_load_world_config(add_worlds_to_sys_path: Path) -> None:
    cfg, root = load_world_config("media_mvp")

    assert cfg.id == "media_mvp"
    assert cfg.scripts[0].loader == "builtin:simple_single_file"
    assert root.name == "media_mvp"


def test_load_scripts(add_worlds_to_sys_path: Path) -> None:
    cfg, root = load_world_config("media_mvp")
    scripts = load_scripts(cfg, root)

    assert set(scripts) == {"media_mvp"}

    script = scripts["media_mvp"]
    assert script.metadata.world_id == cfg.id
    assert script.metadata.entry_label == "start"
    assert script.blocks["start"]["media"][0]["name"] == "test_image.svg"
