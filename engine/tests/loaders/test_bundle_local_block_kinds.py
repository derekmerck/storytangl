"""Bundle-local block kinds contributed through a world's domain module.

A world domain already contributes authorities, story codecs, and a
``class_registry``. The asset compiler resolves ``asset_kind`` through that
registry; block kinds did not, so a bundle could only supply its own block
types by subclassing :class:`StoryCompiler`. These tests cover resolving them
through the ordinary world path instead.
"""

from __future__ import annotations

from pathlib import Path

from tangl.loaders.compiler import WorldCompiler
from tangl.service.world_registry import WorldRegistry
from tangl.story import World
from tangl.story.fabula.compiler import ISSUE_UNRESOLVED_KIND


DOMAIN_SOURCE = '''\
from __future__ import annotations

from tangl.story import Block


class Workshop(Block):
    """A block kind that exists only inside this world bundle."""


class Infirmary(Block):
    """A second contributed kind, to prove it is not a single-name special case."""
'''


def _write_kind_bundle(root: Path, *, label: str, kinds: dict[str, str]) -> Path:
    """Write a world whose domain module contributes its own block kinds.

    ``kinds`` maps block label to the authored ``kind`` string under test.
    """
    bundle_root = root / label
    bundle_root.mkdir()
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
    (bundle_root / f"{module_name}.py").write_text(DOMAIN_SOURCE, encoding="utf-8")

    blocks = []
    for block_label, kind in kinds.items():
        blocks.append(f"      {block_label}:")
        blocks.append(f"        kind: {kind}")
        blocks.append(f"        content: {block_label} content")
    (bundle_root / "story.yaml").write_text(
        "\n".join(
            [
                f"label: {label}",
                "scenes:",
                "  main:",
                "    blocks:",
                *blocks,
            ]
        ),
        encoding="utf-8",
    )
    return bundle_root


def _materialized_kinds(root: Path, label: str) -> dict[str, int]:
    """Compile and materialize the bundle, reporting node kinds by name.

    Materialized counts are the honest end of this contract: a kind that fails
    to resolve does not error, it just shows up as ``Block``.
    """
    World.clear_instances()
    try:
        bundle = WorldRegistry([root]).bundles[label]
        world = WorldCompiler().compile(bundle)
        return dict(world.create_story(f"{label}_probe").report.materialized_counts)
    finally:
        World.clear_instances()


def test_domain_module_block_kinds_resolve_through_the_ordinary_world_path(
    tmp_path: Path,
) -> None:
    """An authored kind naming a contributed class compiles as that class."""
    _write_kind_bundle(
        tmp_path,
        label="kinds_plain",
        kinds={"shop": "Workshop", "clinic": "Infirmary"},
    )

    counts = _materialized_kinds(tmp_path, "kinds_plain")

    assert counts.get("Workshop") == 1, counts
    assert counts.get("Infirmary") == 1, counts
    # Without registry resolution both would silently land here instead.
    assert counts.get("Block", 0) == 0, counts


def test_cardinal_kind_names_win_over_a_contributed_class(tmp_path: Path) -> None:
    """A bundle cannot quietly redefine the cardinal vocabulary.

    The domain module exports classes by name, so a world could otherwise
    shadow ``Block`` itself. Cardinal names resolve first.
    """
    bundle_root = _write_kind_bundle(
        tmp_path,
        label="kinds_shadow",
        kinds={"plain": "Block"},
    )
    (bundle_root / "kinds_shadow_domain.py").write_text(
        DOMAIN_SOURCE
        + '\n\nclass Block(Block):  # noqa: F811 - deliberately shadows the cardinal name\n'
        '    """A world-local class that tries to take the cardinal name."""\n',
        encoding="utf-8",
    )

    counts = _materialized_kinds(tmp_path, "kinds_shadow")

    assert counts.get("Block") == 1, counts
    assert "Workshop" not in counts


def test_unresolved_kind_is_reported_rather_than_silently_downgraded(
    tmp_path: Path,
) -> None:
    """A kind that resolves to nothing produces a diagnostic.

    This is the failure that motivated the change: a world losing its own block
    kinds compiled clean and simply materialized plain ``Block``, so the loss
    was invisible in the report and in the graph.
    """
    _write_kind_bundle(
        tmp_path,
        label="kinds_missing",
        kinds={"ghost": "NoSuchKind"},
    )

    World.clear_instances()
    try:
        bundle = WorldRegistry([tmp_path]).bundles["kinds_missing"]
        world = WorldCompiler().compile(bundle)
    finally:
        World.clear_instances()

    issues = [
        issue for issue in world.bundle.issues if issue.code == ISSUE_UNRESOLVED_KIND
    ]
    assert len(issues) == 1, [issue.code for issue in world.bundle.issues]
    assert issues[0].details["kind"] == "NoSuchKind"
    assert issues[0].details["fallback_kind"] == "Block"
    assert "Workshop" in issues[0].details["known_kinds"]
