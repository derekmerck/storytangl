"""Real media-backed world compilation across two threads."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tangl.service.world_registry import WorldRegistry
from tangl.utils import shelved2


def test_distinct_media_worlds_compile_on_distinct_threads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shelved2, "SHELVED_CACHE_ENABLED", True)
    for label in ("shelf_alpha", "shelf_beta"):
        root = tmp_path / label
        (root / "media").mkdir(parents=True)
        (root / "world.yaml").write_text(
            f"label: {label}\nscripts: story.yaml\nmedia_dir: media\n"
        )
        (root / "story.yaml").write_text(
            f"label: {label}\nscenes:\n  main:\n    blocks:\n      start:\n"
            f"        content: {label}\n"
        )
        (root / "media" / f"{label}.svg").write_text(f"<svg><!-- {label} --></svg>")

    registry = WorldRegistry([tmp_path])
    alpha = registry.get_world("shelf_alpha")
    with ThreadPoolExecutor(max_workers=1) as worker:
        beta = worker.submit(registry.get_world, "shelf_beta").result(timeout=15)
    assert alpha.label == "shelf_alpha" and beta.label == "shelf_beta"
    assert any(record.path.name == "shelf_alpha.svg" for record in alpha.resources.registry.values())
    assert any(record.path.name == "shelf_beta.svg" for record in beta.resources.registry.values())
    assert shelved2.miss_count >= 2
