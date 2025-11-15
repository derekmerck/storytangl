"""Tests for role and setting script reference semantics."""

import pytest

from tangl.ir.story_ir.actor_script_models import ActorScript, RoleScript
from tangl.ir.story_ir.location_script_models import LocationScript, SettingScript


def test_role_script_accepts_template_reference_fields() -> None:
    """Roles should accept template reference metadata."""

    role = RoleScript(
        label="guardian",
        actor_template_ref="guard_template",
        actor_overrides={"rank": "captain"},
        requirement_policy="CREATE",
    )

    assert role.actor_template_ref == "guard_template"
    assert role.actor_template is None
    assert role.actor_overrides == {"rank": "captain"}
    assert role.requirement_policy == "CREATE"


def test_role_script_rejects_both_inline_and_reference_templates() -> None:
    """Roles cannot mix inline templates with template references."""

    with pytest.raises(ValueError, match="Role 'guardian'"):
        RoleScript(
            label="guardian",
            actor_template=ActorScript(label="inline"),
            actor_template_ref="guard_template",
        )


def test_setting_script_accepts_template_reference_fields() -> None:
    """Settings should accept template reference metadata."""

    setting = SettingScript(
        label="courtyard",
        location_template_ref="courtyard_template",
        location_overrides={"terrain": "stone"},
        requirement_policy="EXISTING",
    )

    assert setting.location_template_ref == "courtyard_template"
    assert setting.location_template is None
    assert setting.location_overrides == {"terrain": "stone"}
    assert setting.requirement_policy == "EXISTING"


def test_setting_script_rejects_both_inline_and_reference_templates() -> None:
    """Settings cannot mix inline templates with template references."""

    with pytest.raises(ValueError, match="Setting 'courtyard'"):
        SettingScript(
            label="courtyard",
            location_template=LocationScript(label="inline"),
            location_template_ref="courtyard_template",
        )
