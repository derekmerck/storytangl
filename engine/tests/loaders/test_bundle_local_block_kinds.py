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
from tangl.story import Block, World
from tangl.story.fabula import StoryCompiler
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


def _resolved_block_kind(
    kind: str,
    *,
    class_registry: dict[str, type] | None = None,
) -> tuple[type, list[str]]:
    """Compile one authored block and return its resolved class and issue codes.

    Asserting on the compiled class itself rather than its name matters here:
    a class that shadows a cardinal name necessarily *has* that name, so a
    name-based assertion cannot tell the two apart.
    """
    bundle = StoryCompiler().compile(
        {"label": "probe", "scenes": {"s": {"blocks": {"b": {"kind": kind}}}}},
        class_registry=class_registry,
    )
    resolved = next(
        type(template.payload)
        for template in bundle.template_registry.values()
        if getattr(getattr(template, "payload", None), "label", None) == "b"
    )
    return resolved, [issue.code for issue in bundle.issues]


def test_cardinal_kind_names_win_over_a_contributed_class() -> None:
    """A bundle cannot quietly redefine the cardinal vocabulary.

    The domain module exports classes by name, so a world can hand back a class
    literally called ``Block``. Cardinal names resolve first, so the core class
    is what compiles.
    """

    class Shadow(Block):
        """A world-local class trying to take the cardinal name."""

    Shadow.__name__ = "Block"

    resolved, issues = _resolved_block_kind("Block", class_registry={"Block": Shadow})

    assert resolved is Block
    assert resolved is not Shadow
    assert issues == []


def test_authored_cardinal_kind_matching_the_section_fallback_is_resolved() -> None:
    """``kind: Block`` inside ``blocks`` is a hit, not a miss.

    The cardinal lookup used to answer with the fallback on a miss, which made a
    successful mapping indistinguishable from an absent one whenever the mapped
    class happened to be the section default. That produced a false
    ``compile:unresolved_kind`` on ordinary authored input and let a same-named
    contributed class through despite cardinal precedence.
    """
    resolved, issues = _resolved_block_kind("Block")

    assert resolved is Block
    assert ISSUE_UNRESOLVED_KIND not in issues


def test_bundle_contributed_kind_still_resolves_end_to_end(tmp_path: Path) -> None:
    """Cardinal precedence does not block a world's own names."""
    _write_kind_bundle(tmp_path, label="kinds_mixed", kinds={"shop": "Workshop"})

    counts = _materialized_kinds(tmp_path, "kinds_mixed")

    assert counts.get("Workshop") == 1, counts


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


def _unresolved_issues(script: dict) -> list:
    """Compile a script and return only its unresolved-kind issues."""
    bundle = StoryCompiler().compile(script)
    return [issue for issue in bundle.issues if issue.code == ISSUE_UNRESOLVED_KIND]


def test_scene_kind_path_reports_unresolved_kinds() -> None:
    """The scene call site carries the collector too.

    ``_resolve_kind`` runs at three sites - scene kinds, block kinds, and
    generic section entries. Covering only the block path would let a
    regression that drops the collector from either of the others pass.
    """
    issues = _unresolved_issues(
        {
            "label": "probe",
            "scenes": {"s": {"kind": "NoSuchScene", "blocks": {"b": {}}}},
        }
    )

    assert len(issues) == 1, issues
    assert issues[0].details["kind"] == "NoSuchScene"
    assert issues[0].details["fallback_kind"] == "Scene"
    assert issues[0].source_ref.authored_path == "scenes[0].s"


def test_section_kind_path_reports_unresolved_kinds() -> None:
    """The generic ``_compile_section`` call site carries the collector too."""
    issues = _unresolved_issues(
        {
            "label": "probe",
            "templates": {"t": {"kind": "NoSuchTemplate"}},
            "scenes": {"s": {"blocks": {"b": {}}}},
        }
    )

    assert len(issues) == 1, issues
    assert issues[0].details["kind"] == "NoSuchTemplate"
    assert issues[0].source_ref.authored_path == "templates[0].t"


def test_unresolved_dotted_kind_carries_the_import_reason() -> None:
    """A broken import and an undeclared name are different authoring problems."""
    typo = _unresolved_issues(
        {"label": "p", "scenes": {"s": {"blocks": {"b": {"kind": "NoSuchKind"}}}}}
    )
    broken = _unresolved_issues(
        {"label": "p", "scenes": {"s": {"blocks": {"b": {"kind": "no.such.mod.Thing"}}}}}
    )

    # A bare name is not a claim to be an import path, so there is no reason to
    # report - a rsplit failure would be noise rather than a diagnosis.
    assert "error" not in typo[0].details
    assert broken[0].details["error"].startswith("ModuleNotFoundError")
