"""Import guardrails for manager-first service modules."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "src" / "tangl"
SERVICE_PUBLIC_MODULE = ROOT / "service" / "__init__.py"
BOOTSTRAP_MODULE = ROOT / "service" / "bootstrap.py"


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


def test_service_public_module_no_longer_imports_compatibility_stack() -> None:
    imported = _import_modules(SERVICE_PUBLIC_MODULE)
    forbidden = {"api_endpoint", "gateway", "operations", "orchestrator", "rest_adapter"}
    violations = [module for module in imported if any(name in module for name in forbidden)]
    assert not violations, f"Unexpected compatibility imports: {violations}"


def test_service_bootstrap_only_exposes_manager_builder() -> None:
    imported = _import_modules(BOOTSTRAP_MODULE)
    forbidden = {"controllers", "gateway", "operations", "orchestrator"}
    violations = [module for module in imported if any(name in module for name in forbidden)]
    assert not violations, f"Unexpected compatibility imports: {violations}"
