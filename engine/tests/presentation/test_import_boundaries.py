"""Dependency floor for domain-neutral presentation syntax."""

from __future__ import annotations

import ast
from pathlib import Path


PRESENTATION = Path(__file__).resolve().parents[2] / "src" / "tangl" / "presentation"
ALLOWED_TANGL_PREFIXES = ("tangl.core", "tangl.presentation", "tangl.type_hints")


def _module_name(path: Path) -> str:
    relative = path.relative_to(PRESENTATION).with_suffix("")
    parts = relative.parts[:-1] if path.name == "__init__.py" else relative.parts
    return ".".join(("tangl", "presentation", *parts))


def _imported_tangl_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names if alias.name.startswith("tangl."))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                module_parts = _module_name(path).split(".")
                package = module_parts if path.name == "__init__.py" else module_parts[:-1]
                parent = package[: len(package) - node.level + 1]
                modules.append(".".join((*parent, node.module or "")))
            elif node.module and node.module.startswith("tangl."):
                modules.append(node.module)
    return modules


def test_presentation_imports_only_its_dependency_floor() -> None:
    violations = [
        module
        for path in PRESENTATION.rglob("*.py")
        for module in _imported_tangl_modules(path)
        if not module.startswith(ALLOWED_TANGL_PREFIXES)
    ]

    assert not violations, f"Presentation imports outside its dependency floor: {violations}"
