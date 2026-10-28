"""The owned PersonalName supplies defaults without replacing authored prose policy."""
from __future__ import annotations

import pytest

from tangl.lang.personal_name import PersonalName
from tangl.prose.naming import PersonalNamedActor


@pytest.mark.parametrize(("parts", "expected"), [
    ({"given_name": "Dana", "family_name": "Reyes"}, "Dana"),
    ({"given_name": "Cookie"}, "Cookie"),
    ({"family_name": "Wintermint"}, "Wintermint"),
    ({"aliases": {"Secret"}}, "person"),
    ({}, "person"),
])
def test_default_nominal_and_namespace_follow_the_current_owned_name(
    parts: dict[str, object], expected: str,
) -> None:
    actor = PersonalNamedActor(label="person", personal_name=PersonalName(**parts, title=""))
    assert actor.get_nominal() == expected
    assert actor.get_nominal(form="unknown") == expected
    assert actor.get_ns()["name"] == expected
    assert actor.get_ns()["personal_name"] is actor.personal_name
    assert actor.name == ""
    actor.personal_name = PersonalName(given_name="Ari", family_name="Chen", title="")
    assert actor.get_nominal() == "Ari"
    assert actor.get_ns()["full_name"] == "Ari Chen"
    actor.personal_name.given_name = "Current"
    assert actor.get_nominal() == "Current"
    assert actor.get_ns()["full_name"] == "Current Chen"
    assert actor.name == ""


def test_explicit_display_name_and_proper_forms_policy_is_preserved() -> None:
    actor = PersonalNamedActor(
        label="person", name="The Guide",
        personal_name=PersonalName(given_name="Dana", family_name="Reyes", title=""),
        proper_forms={"proper": "Captain", "full": "Captain Reed"},
    )
    assert actor.get_nominal() == "The Guide"
    assert actor.get_nominal(form="proper") == "Captain"
    assert actor.get_nominal(form="full") == "Captain Reed"
    assert actor.get_ns()["name"] == "The Guide"
    assert actor.get_ns()["full_name"] == "Captain Reed"
    actor.name = ""
    assert actor.get_nominal() == "Captain"
    actor.personal_name.given_name = "Ari"
    assert actor.get_nominal() == "Captain"
    assert actor.personal_name.full_name() == "Ari Reyes"
    actor.personal_name = None
    assert actor.get_nominal() == "person"
    assert actor.get_nominal(form="full") == "Captain Reed"
