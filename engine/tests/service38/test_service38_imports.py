"""Import guardrails for service38 controller isolation."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "src" / "tangl"

IMPLEMENTATION_MODULES = (
    ROOT / "story38" / "story_controller.py",
    ROOT / "story38" / "fabula" / "world_controller.py",
    ROOT / "service38" / "user" / "user_controller.py",
    ROOT / "service38" / "system_controller.py",
)

BARREL_MODULE = ROOT / "service38" / "controllers.py"

BARREL_ALLOWED_IMPORTS = {
    "tangl.story38.story_controller",
    "tangl.story38.fabula.world_controller",
    "tangl.service38.user.user_controller",
    "tangl.service38.system_controller",
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
    if module_name.startswith("tangl.vm38") or module_name.startswith("tangl.story38"):
        return False
    if module_name == "tangl.vm" or module_name.startswith("tangl.vm."):
        return True
    if module_name == "tangl.story" or module_name.startswith("tangl.story."):
        return True
    if module_name == "tangl.service.controllers" or module_name.startswith("tangl.service.controllers."):
        return True
    return False


def test_service38_controller_modules_do_not_import_legacy_story_vm_or_controllers() -> None:
    violations: list[tuple[str, str]] = []
    for path in IMPLEMENTATION_MODULES:
        for module_name in _import_modules(path):
            if _is_legacy_import(module_name):
                violations.append((str(path), module_name))
    assert not violations, f"Legacy imports found: {violations}"


def test_service38_controller_barrel_imports_only_v38_controller_modules() -> None:
    violations: list[str] = []
    for module_name in _import_modules(BARREL_MODULE):
        if module_name == "__future__":
            continue
        if module_name not in BARREL_ALLOWED_IMPORTS:
            violations.append(module_name)
    assert not violations, f"Unexpected barrel imports: {violations}"
