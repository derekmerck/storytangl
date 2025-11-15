from __future__ import annotations

import subprocess
import sys

import pytest

def _run_check(code: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == "False"

@pytest.mark.xfail(reason="This was a good idea, but the script manager has to know about dependencies, consider later.")
def test_import_world_does_not_pull_vm_modules() -> None:
    code = (
        "import importlib, sys; "
        "importlib.import_module('tangl.story.fabula.world'); "
        "print(any(name.startswith('tangl.vm') for name in sys.modules))"
    )
    assert _run_check(code)


def test_import_vm_does_not_pull_story_modules() -> None:
    code = (
        "import importlib, sys; "
        "importlib.import_module('tangl.vm'); "
        "print(any(name.startswith('tangl.story') for name in sys.modules))"
    )
    assert _run_check(code)
