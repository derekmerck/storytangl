"""Family-contract tests for promoted mechanics surfaces.

This module checks a few high-value package-shape promises for the active
mechanics families, especially the promoted presence/look surfaces:
``HasLook``, ``HasOutfit``, ``HasSimpleLook``, and ``OutfitManager``.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tangl.mechanics.presence.look.look import HasLook, HasOutfit, HasSimpleLook
from tangl.mechanics.presence.outfit import OutfitManager


REPO_ROOT = Path(__file__).resolve().parents[3]
MECHANICS_SRC = REPO_ROOT / "engine" / "src" / "tangl" / "mechanics"


def test_look_uses_promoted_outfit_surface() -> None:
    assert HasLook.model_fields["outfit"].annotation is OutfitManager
    assert HasOutfit.model_fields["outfit"].annotation is OutfitManager
    assert "look" in HasSimpleLook.model_fields


def test_active_mechanics_do_not_import_scratch_or_examples() -> None:
    violations: list[str] = []

    for path in MECHANICS_SRC.rglob("*.py"):
        if "examples" in path.parts:
            continue

        module = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported_modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported_modules = [node.module or ""]
            else:
                continue

            for module_name in imported_modules:
                parts = [part for part in module_name.split(".") if part]
                if not parts:
                    continue
                if parts[0] == "scratch":
                    violations.append(f"{path}: imports scratch module {module_name}")
                if "examples" in parts:
                    violations.append(f"{path}: imports example module {module_name}")

    assert violations == [], f"Expected no violations but found: {violations}"
