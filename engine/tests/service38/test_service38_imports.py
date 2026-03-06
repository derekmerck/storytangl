"""Import guardrails for canonical service/story controller isolation."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "src" / "tangl"

def _discover_implementation_modules() -> tuple[Path, ...]:
    modules: list[Path] = []
    for package_root in (ROOT / "story", ROOT / "service" / "controllers"):
        for path in package_root.rglob("*_controller.py"):
            modules.append(path)
    return tuple(sorted(modules))


IMPLEMENTATION_MODULES = _discover_implementation_modules()

BARREL_MODULE = ROOT / "service" / "controllers" / "__init__.py"
BARREL_ALLOWED_IMPORTS = {
    "__future__",
    "runtime_controller",
    "system_controller",
    "user_controller",
    "world_controller",
}


def _import_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                modules.append(node.module)
    return modules


def _is_legacy_import(module_name: str) -> bool:
    retired_prefixes = (
        "tangl.core38",
        "tangl.vm38",
        "tangl.story38",
        "tangl.service38",
        "tangl.core_legacy",
        "tangl.vm_legacy",
        "tangl.story_legacy",
        "tangl.service_legacy",
    )
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in retired_prefixes
    )


def test_controller_modules_do_not_import_retired_namespace_paths() -> None:
    violations: list[tuple[str, str]] = []
    for path in IMPLEMENTATION_MODULES:
        for module_name in _import_modules(path):
            if _is_legacy_import(module_name):
                violations.append((str(path), module_name))
    assert not violations, f"Retired namespace imports found: {violations}"


def test_service_controller_barrel_imports_only_controller_modules() -> None:
    violations: list[str] = []
    for module_name in _import_modules(BARREL_MODULE):
        if module_name not in BARREL_ALLOWED_IMPORTS:
            violations.append(module_name)
    assert not violations, f"Unexpected barrel imports: {violations}"
