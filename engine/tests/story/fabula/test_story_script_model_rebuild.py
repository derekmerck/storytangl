"""Ensure story script models rebuild with path and ancestor tag support."""

from __future__ import annotations

from tangl.ir.story_ir import StoryScript
# from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.ir.core_ir import MasterScript, ScriptMetadata


def test_story_script_model_rebuild_runs_on_import() -> None:
    """Story scripts should validate without manual ``model_rebuild`` calls."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "ancestor_tags": {"town"},
            }
        },
        "scenes": {},
    }

    script = StoryScript.model_validate(story_data)

    assert script.label == "example"
    assert script.templates is not None
    guard = script.templates.get("guard")
    assert guard is not None
    assert guard.req_ancestor_tags == {"town"}
    assert guard.get_selection_criteria()["has_ancestor_tags"] == {"town"}


def test_master_script_model_rebuild_runs_on_import() -> None:
    """Master script should rebuild without path selection defaults."""

    metadata = ScriptMetadata(title="Example", author="Tests")
    script = MasterScript(
        label="example",
        metadata=metadata,
    )

    assert script.label == "example"
    assert script.get_selection_criteria() == {}
