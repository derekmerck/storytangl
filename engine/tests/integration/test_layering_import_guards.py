"""Layering contract tests for core/vm/story/service imports."""

from __future__ import annotations

import ast
from pathlib import Path


def _collect_import_targets(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text())
    targets: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)

    return targets


def _iter_python_modules(package_dir: Path) -> list[Path]:
    return sorted(package_dir.rglob("*.py"))


def test_core_does_not_import_upper_layers() -> None:
    root = Path("engine/src/tangl/core")
    forbidden_prefixes = ("tangl.vm", "tangl.story", "tangl.service")
    violations: list[tuple[str, str]] = []

    for module_path in _iter_python_modules(root):
        for target in _collect_import_targets(module_path):
            if target.startswith(forbidden_prefixes):
                violations.append((str(module_path), target))

    assert violations == []


def test_vm_does_not_import_service_layer() -> None:
    root = Path("engine/src/tangl/vm")
    forbidden_prefixes = ("tangl.service",)
    violations: list[tuple[str, str]] = []

    for module_path in _iter_python_modules(root):
        for target in _collect_import_targets(module_path):
            if target.startswith(forbidden_prefixes):
                violations.append((str(module_path), target))

    assert violations == []


def test_story_does_not_import_service_layer() -> None:
    root = Path("engine/src/tangl/story")
    violations: list[tuple[str, str]] = []

    for module_path in _iter_python_modules(root):
        for target in _collect_import_targets(module_path):
            if target.startswith("tangl.service"):
                violations.append((str(module_path), target))

    assert violations == []
