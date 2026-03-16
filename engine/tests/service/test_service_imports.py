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
def test_service_controller_barrel_imports_only_controller_modules() -> None:
    violations: list[str] = []
    for module_name in _import_modules(BARREL_MODULE):
        if module_name not in BARREL_ALLOWED_IMPORTS:
            violations.append(module_name)
    assert not violations, f"Unexpected barrel imports: {violations}"
