"""Tests for script template path and ancestor tag serialization."""

from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.ir.story_ir.location_script_models import LocationScript



def test_actor_script_scope_serializes_constraints() -> None:
    script = ActorScript(label="smith", path_pattern="village.*")

    assert script.model_dump()["path_pattern"] == "village.*"


def test_location_script_scope_round_trip() -> None:
    script = LocationScript(label="safehouse", ancestor_tags=['conspiracy'])

    ser = script.unstructure_as_template()
    assert ser == {"label": script.label, "ancestor_tags": list(script.req_ancestor_tags)}

    restored = LocationScript.model_validate(ser)

    assert restored.content_hash == script.content_hash
