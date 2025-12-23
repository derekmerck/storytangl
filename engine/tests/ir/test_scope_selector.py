"""Tests for :class:`tangl.ir.story_ir.story_script_models.ScopeSelector`."""

from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.ir.story_ir.location_script_models import LocationScript
# from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_scope_selector_is_global_when_no_constraints() -> None:
    # selector = ScopeSelector()

    assert selector.is_global() is True
    assert selector.model_dump() == {
        "source_label": None,
        "parent_label": None,
        "ancestor_tags": None,
        "ancestor_labels": None,
    }


def test_scope_selector_recognises_constraints() -> None:
    # selector = ScopeSelector(source_label="village.smithy")

    assert selector.is_global() is False
    assert selector.source_label == "village.smithy"


def test_scope_selector_round_trip_serialization() -> None:
    selector = ScopeSelector(
        parent_label="village",
        ancestor_tags={"conspiracy", "mystery"},
        ancestor_labels={"root"},
    )

    dumped = selector.model_dump()
    rehydrated = ScopeSelector.model_validate(dumped)

    assert rehydrated == selector
    assert rehydrated.ancestor_tags == {"conspiracy", "mystery"}
    assert rehydrated.ancestor_labels == {"root"}


def test_actor_script_scope_defaults_to_none() -> None:
    script = ActorScript(label="smith")

    assert script.scope is None
    assert "scope" not in script.model_dump()


def test_actor_script_scope_serializes_constraints() -> None:
    selector = ScopeSelector(parent_label="village")
    script = ActorScript(label="smith", scope=selector)

    assert script.scope is selector
    assert script.model_dump()["scope"] == selector.model_dump(exclude_none=True)


def test_location_script_scope_round_trip() -> None:
    selector = ScopeSelector(ancestor_tags={"conspiracy"})
    script = LocationScript(label="safehouse", scope=selector)

    serialized = {"label": script.label, "scope": selector.model_dump(exclude_none=True)}
    restored = LocationScript.model_validate(serialized)

    assert restored.scope == selector
