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

LEGACY_SOURCE_DIRS = (
    "engine/src/tangl/core/",
    "engine/src/tangl/vm/",
    "engine/src/tangl/story/",
    "engine/src/tangl/service/",
)

SKIP_PATH_PREFIXES = (
    "scratch/",
)

SKIP_PATH_PARTS = {
    "/tests/",
    "/docs/",
}

LEGACY_DEEP_PREFIXES = (
    "tangl.core.",
    "tangl.vm.",
    "tangl.story.",
    "tangl.service.",
)

NAMESPACE38_PREFIXES = (
    "tangl.core38",
    "tangl.vm38",
    "tangl.story38",
    "tangl.service38",
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


def _is_legacy_source(rel_path: str) -> bool:
    return any(rel_path.startswith(prefix) for prefix in LEGACY_SOURCE_DIRS)


def _is_legacy_deep(module: str) -> bool:
    return any(module.startswith(prefix) for prefix in LEGACY_DEEP_PREFIXES)


def _is_38_namespace(module: str) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in NAMESPACE38_PREFIXES)


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
    postswap_38_imports: list[ImportEdge] = []

    for edge in all_edges:
        if _is_ir_bridge(edge) and not _is_legacy_source(edge.path):
            ir_bridge.append(edge)

        if _is_38_namespace(edge.module):
            postswap_38_imports.append(edge)

        if args.mode != "pre-swap":
            continue
        if not _is_legacy_deep(edge.module):
            continue
        if _is_legacy_source(edge.path):
            continue
        if _is_allowed(edge, allow_rules):
            intentional_bridges.append(edge)
        else:
            bypass_imports.append(edge)

    print(f"Cutover import audit mode: {args.mode}")
    _report_block("IR bridge", ir_bridge)
    if args.mode == "pre-swap":
        _report_block("Bypass imports", bypass_imports)
        _report_block("Intentional bridges", intentional_bridges)
    if args.mode == "post-swap":
        _report_block("Post-swap disallowed *38 imports", postswap_38_imports)

    report = {
        "mode": args.mode,
        "ir_bridge": [asdict(edge) for edge in ir_bridge],
        "bypass_imports": [asdict(edge) for edge in bypass_imports],
        "intentional_bridges": [asdict(edge) for edge in intentional_bridges],
        "postswap_38_imports": [asdict(edge) for edge in postswap_38_imports],
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
    if args.mode == "post-swap" and intentional_bridges:
        violations.append(f"Intentional bridge allowlist entries still active: {len(intentional_bridges)}")
    if args.mode == "post-swap" and postswap_38_imports:
        violations.append(f"Post-swap *38 imports present: {len(postswap_38_imports)}")

    if violations:
        print("\nCutover audit failed:")
        for item in violations:
            print(f"- {item}")
        return 2

    print("\nCutover audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
