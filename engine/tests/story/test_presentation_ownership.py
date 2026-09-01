"""Import-ownership tests for Story and mechanic text presentation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run_import_check(source: str) -> None:
    """Run one import-isolation probe in a clean interpreter.

    The probe must import the tree under test. pytest's ``pythonpath`` setting
    does not reach child processes, so without this an installed copy of
    ``tangl`` elsewhere is probed instead — an editable install pointing at
    another checkout, as in a git worktree, silently tests the wrong code.
    """

    roots = [entry for entry in sys.path if entry and Path(entry).name == "src"]
    env = dict(os.environ)
    if roots:
        inherited = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join(roots + ([inherited] if inherited else []))

    result = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def test_story_presentation_does_not_import_optional_mechanics() -> None:
    _run_import_check(
        "import sys; import tangl.story.presentation; "
        "assert not any(name.startswith('tangl.mechanics.') for name in sys.modules)"
    )


def test_presence_presentation_registers_its_own_handlers() -> None:
    _run_import_check(
        "from tangl.mechanics.presence.presentation import ("
        "render_bundle_presence_text, render_look_text, render_ornament_text, "
        "render_outfit_text, render_simple_presence_text); "
        "from tangl.story.dispatch import story_dispatch; "
        "assert all(handler._behavior.uid in story_dispatch.members for handler in ("
        "render_bundle_presence_text, render_look_text, render_ornament_text, "
        "render_outfit_text, render_simple_presence_text))"
    )


def test_credentials_activates_its_presence_presentation_dependency() -> None:
    _run_import_check(
        "import sys; import tangl.mechanics.credentials; "
        "assert 'tangl.mechanics.presence.presentation' in sys.modules"
    )


def test_unrelated_assembly_import_does_not_activate_optional_mechanics() -> None:
    _run_import_check(
        "import sys; import tangl.mechanics.assembly; "
        "assert 'tangl.mechanics.credentials' not in sys.modules; "
        "assert 'tangl.mechanics.presence.presentation' not in sys.modules"
    )
