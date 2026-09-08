"""Media index handlers contributed through a world's domain module.

A world domain module already contributes authorities, story codecs, and a
``class_registry``. Media indexing was the remaining seam: filename-derived
metadata could only be attached by subclassing :class:`MediaCompiler`, even
though ``ResourceManager`` has always accepted ``index_handlers``.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import World


DOMAIN_SOURCE = '''\
from __future__ import annotations

from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT

INDEXED: list[str] = []


def tag_local_media(caller: MediaRIT, *, ctx: object) -> MediaRIT:
    """Attach a world-local tag while the bundle's media is indexed."""
    _ = ctx
    if caller.path is not None:
        INDEXED.append(caller.path.name)
        caller.tags.add(f"local:stem:{caller.path.stem}")
    caller.tags.add("local:indexed")
    return caller


def get_media_index_handlers() -> list[object]:
    return [tag_local_media]
'''

# A world that declares the hook but contributes nothing, to prove the wiring
# does not depend on the hook being present.
BARE_DOMAIN_SOURCE = '''\
from __future__ import annotations
'''


def _write_media_bundle(root: Path, *, label: str, domain_source: str) -> str:
    bundle_root = root / label
    (bundle_root / "media").mkdir(parents=True)
    module_name = f"{label}_domain"

    (bundle_root / "world.yaml").write_text(
        "\n".join(
            [
                f"label: {label}",
                f"domain_module: {module_name}",
                "scripts: story.yaml",
            ]
        ),
        encoding="utf-8",
    )
    (bundle_root / "story.yaml").write_text(
        "\n".join(
            [
                f"label: {label}",
                "scenes:",
                "  main:",
                "    blocks:",
                "      start:",
                "        content: hello",
            ]
        ),
        encoding="utf-8",
    )
    (bundle_root / f"{module_name}.py").write_text(domain_source, encoding="utf-8")
    # A minimal but real SVG, so indexing sees an actual media file.
    (bundle_root / "media" / "sign-north.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',
        encoding="utf-8",
    )
    return module_name


def _compile(root: Path, label: str):
    World.clear_instances()
    try:
        bundle = WorldRegistry([root]).bundles[label]
        return WorldCompiler().compile(bundle)
    finally:
        World.clear_instances()


def _tags(world) -> set[str]:
    return {tag for record in world.resources.registry.values() for tag in record.tags}


def test_domain_module_media_index_handler_runs_during_world_indexing(
    tmp_path: Path,
) -> None:
    """A contributed handler reaches the indexer and its edits persist."""
    module_name = _write_media_bundle(
        tmp_path,
        label="media_local",
        domain_source=DOMAIN_SOURCE,
    )

    world = _compile(tmp_path, "media_local")
    domain_module = importlib.import_module(module_name)

    # Invoked at all, on the real bundle file.
    assert domain_module.INDEXED == ["sign-north.svg"]
    # And the record it returned is the one the world kept.
    tags = _tags(world)
    assert "local:indexed" in tags
    assert "local:stem:sign-north" in tags


def test_media_indexing_works_without_the_hook(tmp_path: Path) -> None:
    """The hook is optional; a domain module need not declare it."""
    _write_media_bundle(
        tmp_path,
        label="media_bare",
        domain_source=BARE_DOMAIN_SOURCE,
    )

    world = _compile(tmp_path, "media_bare")

    assert world.resources is not None
    assert [record.path.name for record in world.resources.registry.values()] == [
        "sign-north.svg"
    ]
    assert not {tag for tag in _tags(world) if tag.startswith("local:")}
