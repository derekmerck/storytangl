"""Import-ownership tests for Story and mechanic text presentation."""

from __future__ import annotations

import subprocess
import sys


def _run_import_check(source: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        check=False,
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
