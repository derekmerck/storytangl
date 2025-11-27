from __future__ import annotations

from pathlib import Path

import pytest

from tangl.media import system_media


def test_get_system_media_context_indexes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    system_media.get_system_media_context.cache_clear()
    media_root = tmp_path / "sys"
    media_root.mkdir()
    asset = media_root / "asset.txt"
    asset.write_text("hello")

    monkeypatch.setattr(system_media, "get_sys_media_dir", lambda: media_root)

    context = system_media.get_system_media_context()

    assert context is not None
    assert context.root == media_root
    rit = context.resource_manager.get_rit("asset.txt")
    assert rit is not None
    assert rit.path == asset

    cached = system_media.get_system_media_context()
    assert cached is context
    assert system_media.get_system_resource_manager() is context.resource_manager


def test_get_system_media_context_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    system_media.get_system_media_context.cache_clear()
    monkeypatch.setattr(system_media, "get_sys_media_dir", lambda: None)

    assert system_media.get_system_media_context() is None
    assert system_media.get_system_resource_manager() is None


def teardown_module() -> None:
    system_media.get_system_media_context.cache_clear()
