#!/usr/bin/env python3
"""Audit namespace-cutover import edges for legacy and transitional modules."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

DEFAULT_ROOTS = (
    "engine/src",
    "apps/cli/src",
    "apps/server/src",
)

TRANSITIONAL_SOURCE_DIRS = (
    "engine/src/tangl/core_legacy/",
    "engine/src/tangl/vm_legacy/",
    "engine/src/tangl/story_legacy/",
    "engine/src/tangl/service_legacy/",
)

SKIP_PATH_PREFIXES = (
    "scratch/",
)

SKIP_PATH_PARTS = {
    "/tests/",
    "/docs/",
}

LEGACY_IMPORT_PREFIXES = (
    "tangl.core_legacy",
    "tangl.vm_legacy",
    "tangl.story_legacy",
    "tangl.service_legacy",
    # Transitional app-only bridges that still route through pre-v38 interfaces.
    "tangl.core.solver",
    "tangl.story.world",
    "tangl.service.service_manager_abc",
)

@dataclass(frozen=True)
class ImportEdge:
    path: str
    module: str
    names: tuple[str, ...]
    lineno: int


@dataclass(frozen=True)
class AllowRule:
    path_glob: str
    import_glob: str

    def matches(self, edge: ImportEdge) -> bool:
        return fnmatch(edge.path, self.path_glob) and fnmatch(edge.module, self.import_glob)


def _iter_python_files(repo_root: Path, roots: Iterable[str]) -> Iterable[Path]:
    for root in roots:
        base = repo_root / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(repo_root).as_posix()
            if any(rel.startswith(prefix) for prefix in SKIP_PATH_PREFIXES):
                continue
            if any(part in f"/{rel}" for part in SKIP_PATH_PARTS):
                continue
            yield path


def _parse_imports(path: Path, repo_root: Path) -> list[ImportEdge]:
    rel = path.relative_to(repo_root).as_posix()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    edges: list[ImportEdge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(
                    ImportEdge(
                        path=rel,
                        module=alias.name,
                        names=(),
                        lineno=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            names = tuple(alias.name for alias in node.names)
            edges.append(
                ImportEdge(
                    path=rel,
                    module=node.module,
                    names=names,
                    lineno=node.lineno,
                )
            )
    return edges


def _load_allow_rules(path: Path) -> list[AllowRule]:
    if not path.exists():
        return []
    rules: list[AllowRule] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise ValueError(
                f"Invalid allowlist line '{line}'. Expected format: path_glob|import_glob"
            )
        path_glob, import_glob = [part.strip() for part in line.split("|", maxsplit=1)]
        rules.append(AllowRule(path_glob=path_glob, import_glob=import_glob))
    return rules


def _has_prefix(module: str, prefixes: Iterable[str]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


def _is_transitional_source(rel_path: str) -> bool:
    return any(rel_path.startswith(prefix) for prefix in TRANSITIONAL_SOURCE_DIRS)


def _is_legacy_import(module: str) -> bool:
    return _has_prefix(module, LEGACY_IMPORT_PREFIXES)


def _is_ir_bridge(edge: ImportEdge) -> bool:
    if edge.module == "tangl.core.factory" or edge.module.startswith("tangl.core.factory."):
        return True
    if "HierarchicalTemplate" in edge.names:
        return True
    return False


def _is_allowed(edge: ImportEdge, rules: list[AllowRule]) -> bool:
    return any(rule.matches(edge) for rule in rules)


def _report_block(name: str, edges: list[ImportEdge]) -> None:
    print(f"- {name}: {len(edges)}")
    for edge in edges:
        names = f" ({', '.join(edge.names)})" if edge.names else ""
        print(f"  - {edge.path}:{edge.lineno} -> {edge.module}{names}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("pre-swap", "post-swap"),
        default="pre-swap",
        help="Audit mode for staged cutover gate behavior.",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Return non-zero when gate criteria are violated.",
    )
    parser.add_argument(
        "--allowlist",
        default="scripts/cutover_import_allowlist.txt",
        help="Path to allowlist rules file (path_glob|import_glob).",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional JSON report output path.",
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=list(DEFAULT_ROOTS),
        help="Roots to scan relative to repository root.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    allow_rules = _load_allow_rules((repo_root / args.allowlist).resolve())

    all_edges: list[ImportEdge] = []
    for py_file in _iter_python_files(repo_root, args.roots):
        all_edges.extend(_parse_imports(py_file, repo_root))

    ir_bridge: list[ImportEdge] = []
    bypass_imports: list[ImportEdge] = []
    intentional_bridges: list[ImportEdge] = []
    postswap_legacy_imports: list[ImportEdge] = []

    for edge in all_edges:
        source_is_transitional = _is_transitional_source(edge.path)

        if _is_ir_bridge(edge) and not source_is_transitional:
            ir_bridge.append(edge)

        if source_is_transitional:
            continue

        if not _is_legacy_import(edge.module):
            continue

        if _is_allowed(edge, allow_rules):
            intentional_bridges.append(edge)
            continue

        if args.mode == "pre-swap":
            bypass_imports.append(edge)
        else:
            postswap_legacy_imports.append(edge)

    print(f"Cutover import audit mode: {args.mode}")
    _report_block("IR bridge", ir_bridge)
    if args.mode == "pre-swap":
        _report_block("Bypass imports", bypass_imports)
        _report_block("Intentional bridges", intentional_bridges)
    if args.mode == "post-swap":
        _report_block("Post-swap disallowed legacy imports", postswap_legacy_imports)

    report = {
        "mode": args.mode,
        "ir_bridge": [asdict(edge) for edge in ir_bridge],
        "bypass_imports": [asdict(edge) for edge in bypass_imports],
        "intentional_bridges": [asdict(edge) for edge in intentional_bridges],
        "postswap_legacy_imports": [asdict(edge) for edge in postswap_legacy_imports],
    }

    if args.json_out:
        out_path = (repo_root / args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote JSON report: {out_path}")

    if not args.enforce:
        return 0

    violations: list[str] = []
    if ir_bridge:
        violations.append(f"IR bridge edges present: {len(ir_bridge)}")
    if bypass_imports:
        violations.append(f"Bypass imports present: {len(bypass_imports)}")
    if args.mode == "post-swap" and postswap_legacy_imports:
        violations.append(
            f"Post-swap legacy imports present: {len(postswap_legacy_imports)}"
        )
    if args.mode == "post-swap" and intentional_bridges:
        violations.append(
            f"Intentional bridge allowlist entries still active: {len(intentional_bridges)}"
        )

    if violations:
        print("\nCutover audit failed:")
        for item in violations:
            print(f"- {item}")
        return 2

    print("\nCutover audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
