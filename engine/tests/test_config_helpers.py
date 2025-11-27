from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tangl import config


def _make_settings(*, worlds: list[str | Path] | None, system_media: str | Path | None):
    paths = SimpleNamespace(worlds=worlds, system_media=system_media)
    service = SimpleNamespace(paths=paths)
    return SimpleNamespace(service=service)


def test_get_world_dirs_casts_to_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw_path = tmp_path / "worlds"
    monkeypatch.setattr(config, "settings", _make_settings(worlds=[str(raw_path)], system_media=None))

    result = config.get_world_dirs()

    assert result == [raw_path]
    assert all(isinstance(item, Path) for item in result)


def test_get_world_dirs_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "settings", _make_settings(worlds=None, system_media=None))

    assert config.get_world_dirs() == []


def test_get_sys_media_dir_optional(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "settings", _make_settings(worlds=None, system_media=str(tmp_path)))

    assert config.get_sys_media_dir() == tmp_path

    monkeypatch.setattr(config, "settings", _make_settings(worlds=None, system_media=None))

    assert config.get_sys_media_dir() is None
