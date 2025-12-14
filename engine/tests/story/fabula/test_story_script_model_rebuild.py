"""Ensure :class:`StoryScript` is rebuilt with ``ScopeSelector`` available."""

from __future__ import annotations

from tangl.ir.story_ir import StoryScript
from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_story_script_model_rebuild_runs_on_import() -> None:
    """Story scripts should validate without manual ``model_rebuild`` calls."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "scope": {"ancestor_tags": {"town"}},
            }
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(story_data)

    assert script.label == "example"
    assert script.templates is not None
    guard = script.templates.get("guard")
    assert guard is not None
    scope = guard.get("scope")
    assert scope is not None
    assert scope.get("ancestor_tags") == ScopeSelector(ancestor_tags={"town"}).ancestor_tags
