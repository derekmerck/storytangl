"""Checkout-first environments for tests that start fresh interpreters."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = REPO_ROOT / "engine" / "src"
TESTS_ROOT = REPO_ROOT / "engine" / "tests"


def checkout_env(*extra_roots: Path) -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(ENGINE_SRC), *(str(path) for path in extra_roots)]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env
