"""Dependency floor for domain-neutral presentation syntax."""

from __future__ import annotations

import ast
from pathlib import Path


PRESENTATION = Path(__file__).resolve().parents[2] / "src" / "tangl" / "presentation"
FORBIDDEN_PREFIXES = (
    "tangl.story",
    "tangl.mechanics",
    "tangl.service",
    "worlds",
    "apps",
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_presentation_does_not_import_domain_or_adapter_layers() -> None:
    violations = [
        module
        for path in PRESENTATION.glob("*.py")
        for module in _imported_modules(path)
        if module.startswith(FORBIDDEN_PREFIXES)
    ]

    assert not violations, f"Presentation imports forbidden layers: {violations}"
